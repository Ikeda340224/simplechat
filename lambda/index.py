# lambda/index.py
import json
import os
import boto3
import re  # 正規表現モジュールをインポート
from botocore.exceptions import ClientError
import urllib.request


# Lambda コンテキストからリージョンを抽出する関数
def extract_region_from_arn(arn):
    # ARN 形式: arn:aws:lambda:region:account-id:function:function-name
    match = re.search('arn:aws:lambda:([^:]+):', arn)
    if match:
        return match.group(1)
    return "us-east-1"  # デフォルト値

# グローバル変数としてクライアントを初期化（初期値）
#bedrock_client = None

# モデルID
#MODEL_ID = os.environ.get("MODEL_ID", "us.amazon.nova-lite-v1:0")
MODEL_ID = "https://ddb3-34-125-58-200.ngrok-free.app"

def lambda_handler(event, context):
    try:

        print("Received event:", json.dumps(event))

        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")

        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])

        print("Processing message:", message)
        print("Using model:", MODEL_ID)

        # 会話履歴を使用
        messages = conversation_history.copy()

        # ユーザーメッセージを追加
        messages.append({
            "role": "user",
            "content": message
        })

        #リクエストペイロード
        request_payload = {
            "prompt": message,
            "max_new_tokens": 512,  ###      
            "do_sample": True,
            "temperature": 0.7,
            "top_p": 0.9  ###
        }

        data = json.dumps(request_payload).encode('utf-8')
        print("request to FastAPI:", json.dumps(request_payload))

        response = {
            "generated_text": "string",
            "response_time": 0}
        url = f"{MODEL_ID}/generate"

        req = urllib.request.Request(
                    url=url,
                    data=data,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
        )

        with urllib.request.urlopen(req) as response:
           response_body = json.loads(response.read().decode('utf-8'))


        print("Fast API response:", json.dumps(response_body, default=str))

        # 応答の検証
        if not response_body.get('generated_text'):
                raise Exception("No response content from the model")

        # アシスタントの応答を取得
        assistant_response = response_body['generated_text']

        # アシスタントの応答を会話履歴に追加
        messages.append({
            "role": "assistant",
            "content": assistant_response
        })

        # 成功レスポンスの返却
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": messages
            })
        }

    except Exception as error:
        print("Error:", str(error))

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }
             