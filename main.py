import sys
from datetime import datetime, timedelta
import holidays
from dotenv import load_dotenv
from utils.telegram_util import TelegramUtil
from utils.api_util import ApiUtil, ApiError
from utils.logger_util import LoggerUtil
import os
import imgkit
import requests
from bs4 import BeautifulSoup
import re
load_dotenv()

def main():
    logger = LoggerUtil().get_logger()
    telegram = TelegramUtil()
    api_util = ApiUtil()
    wkhtmltoimage_path = os.getenv('WKHTMLTOIMAGE_PATH')

    # https://comp.fnguide.com/SVO2/ASP/SVD_Report_Summary_Data.asp?fr_dt=20250305&to_dt=20250305&check=all 링크 크롤링해서 HTML 태그 값 가져온 다음에 다시 꾸며서 imgkit 라이브러리로 이미지 생성
    today = datetime.now().strftime("%Y%m%d")
    url = f"https://comp.fnguide.com/SVO2/ASP/SVD_Report_Summary_Data.asp?fr_dt={today}&to_dt={today}&check=all"
    response = requests.get(url)
    html = response.text
    
    # BeautifulSoup으로 HTML 파싱하여 데이터 유무 확인
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.find_all('tr')
    
    # rows가 비어있는 경우 처리
    if not rows:
        logger.warning(f"{today} - 리포트 데이터가 없습니다. 프로그램을 종료합니다.")
        return  # 함수 종료
    
    # 데이터가 있는 경우 계속 진행
    # HTML 데이터 가공 및 스타일 추가
    html_pages = process_html(html, today)

    options = {
        'format': 'png',
        'encoding': "UTF-8",
        'quality': 75,  # 품질을 75%로 낮춰서 파일 크기 감소
        'width': 1200,   # 너비를 900px로 조정
        'enable-local-file-access': None,
        'minimum-font-size': 12,
        'quiet': None   # 로그 레벨 조정
    }

    try:
        if not wkhtmltoimage_path:
            message = "오류 발생\n\nWKHTMLTOIMAGE_PATH 환경변수가 설정되지 않았습니다."
            logger.error(message)
            raise ValueError(message)

        # 현재 스크립트 파일이 있는 디렉토리를 기준으로 output 폴더 경로 설정
        current_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(current_dir, 'output')
        
        # output 디렉토리가 없으면 생성
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"output 디렉토리 생성: {output_dir}")
            
        # 이전 파일 삭제
        for old_file in os.listdir(output_dir):
            if old_file.startswith('output_') and old_file.endswith('.png'):
                os.remove(os.path.join(output_dir, old_file))
                logger.info(f"기존 파일 삭제: {old_file}")

        config = imgkit.config(wkhtmltoimage=wkhtmltoimage_path)
        
        # HTML을 페이지별로 생성하고 이미지 저장
        image_paths = []
        for page_num, page_html in enumerate(html_pages, 1):
            file_path = os.path.join(output_dir, f"output_{today}_{page_num}p.png")
            imgkit.from_string(page_html, file_path, options=options, config=config)
            logger.info(f"새 파일 저장: {file_path}")
            image_paths.append(file_path)
        
        # 텔레그램으로 이미지 전송
        formatted_date = f"{today[:4]}-{today[4:6]}-{today[6:]}"
        caption = f"{formatted_date} 증권사 리포트 요약"
        telegram.send_multiple_photo(image_paths, caption)
        
        # API로 이미지 전송 
        try:
            api_util.create_post(
                title=caption,
                content="증권사 리포트 요약 데이터",
                category="증권사리포트",
                writer="admin",
                image_paths=image_paths,
                thumbnail_image_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'thumbnail', 'thumbnail.png')
            )
        except ApiError as e:
            message = f"❌ API 오류 발생\n\n{e.message}"
            telegram.send_test_message(message)
            logger.error(message)
        
    except Exception as e:
        message = f"오류 발생 이미지 생성\n오류: {str(e)}"
        logger.error(message)
        raise ValueError(message)

def process_html(html, today):
    """HTML 데이터를 가공하여 보기 좋은 테이블 형태로 변환"""
    # 날짜 형식 변환 (YYYYMMDD -> YYYY-MM-DD)
    formatted_date = f"{today[:4]}-{today[4:6]}-{today[6:]}"
    
    # BeautifulSoup으로 HTML 파싱
    soup = BeautifulSoup(html, 'html.parser')
    
    # 종목 정보 추출
    stock_data = []
    
    # 테이블 행(tr) 요소들 찾기
    rows = soup.find_all('tr')
    
    for row in rows:
        # 종목명과 코드 추출
        stock_name_tag = row.select_one('td.l.nopre dl.um_tdinsm dt a')
        if stock_name_tag:
            # 종목명에서 코드 부분 제거
            full_text = stock_name_tag.get_text().strip()
            
            # 종목코드 추출
            code_tag = row.select_one('td.l.nopre dl.um_tdinsm dt a span.txt1')
            stock_code = code_tag.get_text().strip() if code_tag else ""
            
            # 종목코드에서 'A' 제거
            if stock_code.startswith('A'):
                stock_code = stock_code[1:]
            
            # 종목명에서 종목코드 부분 제거
            stock_name = full_text.replace(code_tag.get_text().strip() if code_tag else "", "").strip()
            
            # 내용 추출 (제목 부분)
            title_tag = row.select_one('td.l.nopre dl.um_tdinsm dt span.txt2')
            title = title_tag.get_text().strip() if title_tag else ""
            if title.startswith('-'):  # 제목이 하이픈(-)으로 시작하는 경우
                title = title[1:].strip()  # 첫 번째 문자 제거 후 공백 제거
            
            # 내용 추출 (상세 내용)
            content_tags = row.select('td.l.nopre dl.um_tdinsm dd')
            content_items = []
            for tag in content_tags:
                text = tag.get_text().strip()
                if text:  # 빈 텍스트가 아닌 경우만 추가
                    content_items.append(f"• {text}")
            
            content = "\n".join(content_items) if content_items else ""
            
            # 현재가 추출
            current_price_tag = row.select_one('td.r:nth-of-type(5)')
            current_price = current_price_tag.get_text().strip() if current_price_tag else ""
            
            # 증권사 및 작성자 추출 (img 태그 제외하고 <br> 유지)
            analyst_tag = row.select_one('td.cle.c.nopre2 span.gpbox')
            if analyst_tag:
                # img 태그 제거
                for img in analyst_tag.find_all('img'):
                    img.decompose()
                
                # <br> 태그를 줄바꿈으로 변환
                analyst_html = str(analyst_tag)
                analyst = analyst_html.replace('<br/>', '\n').replace('<br>', '\n')
                # HTML 태그 제거
                analyst = re.sub('<[^<]+?>', '', analyst).strip()
            else:
                analyst = ""
            
            # 투자의견 추출
            opinion_tag = row.select_one('td.c.nopre2:nth-of-type(3) span.gpbox')
            opinion = opinion_tag.get_text().strip() if opinion_tag else ""
            
            # 목표가 추출 및 상향/하향 정보 확인
            target_price_tag = row.select_one('td.r.nopre2:nth-of-type(4) span.gpbox')
            target_price = target_price_tag.get_text().strip() if target_price_tag else ""
            
            # 상향/하향 이미지 태그 확인
            target_price_img = target_price_tag.select_one('img.gp_img') if target_price_tag else None
            target_price_direction = ""
            is_new = False
            if target_price_img:
                img_classes = target_price_img.get('class', [])
                if 'up' in img_classes:
                    target_price_direction = "up"
                elif 'down' in img_classes:
                    target_price_direction = "down"
                
                # 새로운 종목 확인 (별도로 체크)
                if 'new' in img_classes:
                    is_new = True
            
            stock_data.append({
                'name': stock_name,
                'code': stock_code,
                'title': title,
                'content': content,
                'current_price': current_price,
                'analyst': analyst,
                'opinion': opinion,
                'target_price': target_price,
                'target_price_direction': target_price_direction,
                'is_new': is_new
            })
    
    # 기본 HTML 구조 생성
    html_pages = []
    items_per_page = 10
    total_pages = (len(stock_data) + items_per_page - 1) // items_per_page

    for page in range(total_pages):
        start_idx = page * items_per_page
        end_idx = min((page + 1) * items_per_page, len(stock_data))
        current_page_data = stock_data[start_idx:end_idx]

        processed_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
            <title>{formatted_date} 증권사 리포트 요약</title>
            <style>
                body {{
                    font-family: 'Noto Sans KR', sans-serif;
                    margin: 20px;
                    padding: 0;
                    color: #333;
                    font-size: 14px;
                }}
                h1 {{
                    text-align: center;
                    font-size: 28px;
                    margin-bottom: 25px;
                    font-weight: bold;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 15px;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 12px;
                    text-align: center;
                    vertical-align: middle;
                    font-size: 14px;
                    line-height: 1.4;
                }}
                th {{
                    background-color: #333;
                    color: white;
                    font-weight: bold;
                    font-size: 15px;
                    padding: 15px;
                }}
                tr:nth-child(odd) {{
                    background-color: #f9f9f9;
                }}
                .source {{
                    text-align: right;
                    color: #888;
                    font-size: 13px;
                    margin-top: 8px;
                }}
                .source-main {{
                    font-size: 13px;
                    margin-bottom: 3px;
                }}
                .source-sub {{
                    font-size: 11px;
                    color: #999;
                }}
                .stock-name {{
                    text-align: center;
                    font-weight: bold;
                    white-space: pre-line;
                    font-size: 15px;
                }}
                .content {{
                    text-align: left;
                    max-width: 450px;
                }}
                .content-title {{
                    font-weight: bold;
                    margin-bottom: 8px;
                    font-size: 15px;
                }}
                .content-detail {{
                    font-size: 14px;
                    color: #555;
                    white-space: pre-line;
                    text-align: left;
                    line-height: 1.5;
                }}
                .price {{
                    text-align: right;
                    font-size: 14px;
                }}
                .price-up {{
                    color: #e53935;
                    font-weight: bold;
                }}
                .price-up::before {{
                    content: "▲ ";
                }}
                .price-down {{
                    color: #1565c0;
                    font-weight: bold;
                }}
                .price-down::before {{
                    content: "▼ ";
                }}
                .price-new {{
                    color: #ff9800;
                    font-weight: bold;
                }}
                .price-new::before {{
                    content: "N ";
                    background-color: #ff9800;
                    color: white;
                    padding: 0 3px;
                    border-radius: 3px;
                    margin-right: 3px;
                }}
                .analyst {{
                    font-size: 14px;
                    white-space: pre-line;
                    line-height: 1.4;
                }}
            </style>
        </head>
        <body>
            <h1>{formatted_date} 증권사 리포트 요약({page + 1}/{total_pages})</h1>
            <table>
                <tr>
                    <th>종목명</th>
                    <th>내용</th>
                    <th>투자의견</th>
                    <th>목표주가</th>
                    <th>전일종가</th>
                    <th>증권사/작성자</th>
                </tr>
        """

        # 현재 페이지의 종목 데이터 추가
        for stock in current_page_data:
            processed_html += f"""
                <tr>
                    <td class="stock-name">{stock['name']}\n({stock['code']})</td>
                    <td class="content">
                        <div class="content-title">{stock['title']}</div>
                        <div class="content-detail">{stock['content']}</div>
                    </td>
                    <td>{stock['opinion']}</td>
                    <td class="price{' price-up' if stock['target_price_direction'] == 'up' else ' price-down' if stock['target_price_direction'] == 'down' else ''}{' price-new' if stock['is_new'] else ''}">{stock['target_price']}</td>
                    <td class="price">{stock['current_price']}</td>
                    <td class="analyst">{stock['analyst']}</td>
                </tr>
            """

        # HTML 마무리
        processed_html += """
            </table>
            <div class="source">
                <div class="source-main">※ 출처 : MQ(Money Quotient)</div>
                <div class="source-sub">본 데이터는 FnGuide의 요약리포트를 참고하였습니다.</div>
            </div>
        </body>
        </html>
        """
        
        html_pages.append(processed_html)

    return html_pages

if __name__ == "__main__":
    main()
