import requests
import json

# 测试知识库文件上传功能
def test_file_upload():
    # 创建知识库
    kb_data = {
        "name": "Test Knowledge Base",
        "description": "Test knowledge base for file upload",
        "chunk_size": 1000,
        "chunk_overlap": 200
    }

    # 创建知识库
    response = requests.post("http://localhost:8081/api/v1/knowledge-bases/", json=kb_data)
    print(f"Create KB status: {response.status_code}")
    if response.status_code == 200:
        kb = response.json()
        kb_id = kb["id"]
        print(f"Created knowledge base with ID: {kb_id}")

        # 上传文件
        with open("test.txt", "w", encoding="utf-8") as f:
            f.write("This is a test file for uploading to knowledge base. " * 100)

        with open("test.txt", "rb") as f:
            files = {"file": ("test.txt", f, "text/plain")}
            response = requests.post(f"http://localhost:8081/api/v1/knowledge-bases/{kb_id}/files", files=files)
            print(f"Upload file status: {response.status_code}")
            if response.status_code == 200:
                file_data = response.json()
                print(f"Uploaded file: {file_data['filename']}")
            else:
                print(f"Upload failed: {response.text}")
    else:
        print(f"KB creation failed: {response.text}")

if __name__ == "__main__":
    test_file_upload()