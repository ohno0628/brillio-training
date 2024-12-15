from flask import Flask, request, jsonify, render_template
import boto3
import pymysql

app = Flask(__name__)

# AWSリソース設定
S3_BUCKET = 'image-upload-app-bucket-ohno'
s3 = boto3.client('s3')

# RDS接続設定
connection = pymysql.connect(
    host='database-1.c3ieg4gami7e.ap-northeast-1.rds.amazonaws.com',
    user='admin',
    password='Ohno!3340',
    database='image_app'
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    title = request.form['title']
    description = request.form['description']

    # S3にアップロード
    s3.upload_fileobj(file, S3_BUCKET, file.filename)

    # DBに保存
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO images (title, description, file_path) VALUES (%s, %s, %s)",
            (title, description, f"https://{S3_BUCKET}.s3.amazonaws.com/{file.filename}")
        )
        connection.commit()

    return jsonify({'message': 'File uploaded successfully'})

@app.route('/images', methods=['GET'])
def list_images():
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, title, description, file_path FROM images")
        rows = cursor.fetchall()
    result = [
        {"id": row[0], "title": row[1], "description": row[2], "file_path": row[3]}
        for row in rows
    ]
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

