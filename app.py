from flask import Flask, request, jsonify, redirect, render_template_string
from flask_cors import CORS
import random
import string
import sqlite3
import validators
from datetime import datetime
import urllib.parse  # Add this import to use unquote

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://huynhcacduythuan.github.io"}})  # Allow requests from localhost:3000

def is_valid_url(url):
    return validators.url(url)

def get_db_connection():
    conn = sqlite3.connect('urls.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_table():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_url TEXT NOT NULL,
            short_url TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            click_count INTEGER DEFAULT 0  -- Add click_count column to track accesses
        )
    ''')
    conn.commit()
    conn.close()

def generate_short_url():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

@app.route('/')
def home():
    return "Welcome to the URL shortener API! Use /shorten to shorten URLs."

@app.route('/shorten', methods=['POST'])
def shorten_url():
    original_url = request.json.get('url')

    if not original_url:
        return jsonify({'error': 'No URL provided'}), 400
    
    # Kiểm tra URL hợp lệ
    if not is_valid_url(original_url):
        return jsonify({'error': 'Invalid URL format'}), 400

    # Tạo short URL
    short_url = generate_short_url()

    # Lấy thời gian hiện tại
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Lưu ngày giờ hiện tại

    # Lưu vào cơ sở dữ liệu
    conn = get_db_connection()
    conn.execute('INSERT INTO urls (original_url, short_url, created_at) VALUES (?, ?, ?)', 
                 (original_url, short_url, created_at))
    conn.commit()
    conn.close()

    return jsonify({
        'original_url': original_url,
        'short_url': f"/{short_url}",
        'created_at': created_at  # You can also return the creation date if needed
    })

@app.route('/<short_url>', methods=['GET'])
def redirect_url(short_url):
    conn = get_db_connection()
    url = conn.execute('SELECT * FROM urls WHERE short_url = ?', (short_url,)).fetchone()

    if url is None:
        return jsonify({'error': 'URL not found'}), 404

    # Tăng số lần nhấp cho URL rút gọn này
    conn.execute('UPDATE urls SET click_count = click_count + 1 WHERE short_url = ?', (short_url,))
    conn.commit()
    conn.close()

    # Kiểm tra User-Agent để xác định thiết bị
    user_agent = request.headers.get('User-Agent')

    # Nếu người dùng đang truy cập bằng điện thoại, gán link rút gọn đặc biệt
    if "Mobile" in user_agent or "Android" in user_agent or "iPhone" in user_agent:
        url_goc = "https://www.shopee.vn/"  # Chuyển hướng đến trang Shopee trước
        app_url = "shopeevn://home?navRoute=eyJwYXRoc"  # Deep link cho ứng dụng Shopee
        web_url = "https://shopee.vn/universal-link/m/shopee-tech-zone"  # Fallback đến trang web Shopee

        # Chuyển hướng đến trang web Shopee trước, sau đó sẽ xử lý chuyển tiếp đến ứng dụng Shopee trong 3 giây
        return render_template_string("""
            <html>
                <head>
                    <meta http-equiv="refresh" content="3;url={{ app_url }}">
                    <script type="text/javascript">
                        // Sau 3 giây, chuyển hướng tới ứng dụng Shopee hoặc fallback
                        setTimeout(function() {
                            window.location = "{{ app_url }}";
                        }, 8000);
                    </script>
                </head>
                <body>
                   
                </body>
            </html>
        """, app_url=app_url, web_url=web_url)  # Trả về trang HTML với script JavaScript

    # Nếu URL gốc chứa shopee.vn, redirect đến một URL khác (ví dụ: YouTube)
    if 'shopee.vn' in url['original_url']:
        youtube_search_url = "https://www.youtube.com/results?search_query=deploy+backend+python+free"
        return redirect(youtube_search_url, code=302)

    # Kiểm tra xem có phải đang sử dụng Facebook Debugger không
    if "facebookexternalhit" in user_agent:
        # Trả về link ảo cho Facebook Debugger
        debug_info = {
            "short_url": short_url,
            "original_url": "https://example.com/virtual-link",  # Link ảo cho Debug
            "description": "This is a short link redirecting to the virtual link for Facebook Debugger."
        }
        return jsonify(debug_info)

    # Nếu không phải điện thoại hoặc Facebook Debugger, chuyển hướng tới URL gốc
    return redirect(url['original_url'], code=302)  # Chuyển hướng đến URL gốc với mã trạng thái 302

@app.route('/update/<short_url>', methods=['POST'])
def update_url1(short_url):
    # Nhận URL mới và short URL mới từ yêu cầu
    new_short_url = request.json.get('new_short_url')
    new_original_url = request.json.get('url')

    if not new_original_url or not new_short_url:
        return jsonify({'error': 'Both new URL and short URL are required!'}), 400

    # Kết nối cơ sở dữ liệu và tìm kiếm URL ngắn cũ
    conn = get_db_connection()
    url = conn.execute('SELECT * FROM urls WHERE short_url = ?', (short_url,)).fetchone()

    if url is None:
        return jsonify({'error': 'Short URL not found'}), 404

    # Kiểm tra nếu short URL mới đã tồn tại trong cơ sở dữ liệu (để tránh xung đột)
    existing_short_url = conn.execute('SELECT * FROM urls WHERE short_url = ?', (new_short_url,)).fetchone()
    if existing_short_url:
        return jsonify({'error': 'Short URL already exists. Please choose a different one.'}), 400

    # Cập nhật URL gốc và short URL trong cơ sở dữ liệu
    conn.execute('UPDATE urls SET original_url = ?, short_url = ? WHERE short_url = ?',
                 (new_original_url, new_short_url, short_url))
    conn.commit()
    conn.close()

    return jsonify({
        'message': 'URL and Short URL updated successfully',
        'new_short_url': f'/{new_short_url}',
        'updated_url': new_original_url
    })



@app.route('/all', methods=['GET'])
def get_all_urls():
    # Connect to the database
    conn = get_db_connection()
    
    # Execute the SQL query to fetch all records from the urls table
    urls = conn.execute('SELECT * FROM urls').fetchall()
    conn.close()

    # If there are no URLs, return an appropriate message
    if not urls:
        return jsonify({'message': 'No shortened URLs found'}), 404

    # Convert the results into a list of dictionaries to send as JSON
    urls_list = []
    for url in urls:
        urls_list.append({
            'original_url': url['original_url'],
            'short_url': f"/{url['short_url']}",
            'created_at': url['created_at']
        })

    return jsonify(urls_list)
@app.route('/update1/<short_url>', methods=['POST'])
def update_url(short_url):
    # Ensure you're decoding the short URL correctly
    decoded_short_url = urllib.parse.unquote(short_url)

    # Get the new original URL from the request body
    new_original_url = request.json.get('new_original_url')

    if not new_original_url:
        return jsonify({'error': 'New original URL is required!'}), 400  # Validation for the new original URL

    # Connect to the database and search for the existing short URL
    conn = get_db_connection()
    url = conn.execute('SELECT * FROM urls WHERE short_url = ?', (decoded_short_url,)).fetchone()

    if url is None:
        return jsonify({'error': 'Short URL not found'}), 404

    # Update only the original URL in the database (keep the short URL intact)
    conn.execute('UPDATE urls SET original_url = ? WHERE short_url = ?',
                 (new_original_url, decoded_short_url))
    conn.commit()
    conn.close()

    return jsonify({
        'message': 'Original URL updated successfully',
        'updated_url': new_original_url
    })



@app.route('/stats', methods=['GET'])
def get_stats():
    conn = get_db_connection()

    # Get total number of shortened URLs
    total_urls = conn.execute('SELECT COUNT(*) FROM urls').fetchone()[0]

    # Get today's date in 'YYYY-MM-DD' format
    today = datetime.now().strftime('%Y-%m-%d')

    # Get the total number of URLs created today
    total_urls_today = conn.execute('SELECT COUNT(*) FROM urls WHERE created_at LIKE ?', (today + '%',)).fetchone()[0]

    # Get the total click counts for today
    total_clicks_today = conn.execute('SELECT SUM(click_count) FROM urls WHERE created_at LIKE ?', (today + '%',)).fetchone()[0]

    # Get the click counts for each URL (no date filter)
    click_stats = conn.execute('SELECT short_url, click_count FROM urls').fetchall()
    conn.close()

    # Format the response
    stats = {
        'total_urls': total_urls,
        'total_urls_today': total_urls_today,  # Add total URLs created today
        'total_clicks_today': total_clicks_today,  # Add total clicks today
        'click_counts': []
    }

    for stat in click_stats:
        stats['click_counts'].append({
            'short_url': stat['short_url'],
            'click_count': stat['click_count']
        })

    return jsonify(stats)



@app.route('/stats/daily', methods=['GET'])
def get_daily_stats():
    # Get the current date in 'YYYY-MM-DD' format
    today = datetime.now().strftime('%Y-%m-%d')

    conn = get_db_connection()
    
    # Query the database to count clicks per short_url for today
    query = '''
        SELECT short_url, COUNT(*) as click_count
        FROM urls
        WHERE created_at LIKE ?
        GROUP BY short_url
    '''
    daily_stats = conn.execute(query, (today + '%',)).fetchall()
    conn.close()

    if not daily_stats:
        return jsonify({'message': 'No statistics available for today.'}), 404

    # Format the response
    stats = {
        'date': today,
        'click_counts': []
    }

    for stat in daily_stats:
        stats['click_counts'].append({
            'short_url': stat['short_url'],
            'click_count': stat['click_count']
        })

    return jsonify(stats)

if __name__ == '__main__':
    create_table()  # Tạo bảng khi chạy ứng dụng
    app.run(debug=True, host="0.0.0.0", port=10000)
