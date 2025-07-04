import os
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
from supabase import create_client, Client
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

# FastAPIアプリケーションのインスタンスを作成
app = FastAPI()

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では具体的なドメインを指定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabaseクライアントの初期化
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# リクエストボディのバリデーション用モデル
class LoginRequest(BaseModel):
    username: str
    password: str

# レスポンスモデル
class LoginResponse(BaseModel):
    success: bool
    message: str
    user_id: int = None

# ルートURLにアクセスがあった場合に実行される関数
@app.get("/")
async def hello_world():
    return 'Hello, World!'

# /nightにアクセスがあった場合に実行される関数
@app.get("/night")
async def hello_night_world():
    return 'Good night!'

# /night/{id}にアクセスがあった場合に実行される関数
@app.get("/night/{id}")
async def good_night(id: str):
    return f'{id}さん、「早く寝てね」'

# '/login'エンドポイントを定義
@app.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    try:
        # Supabaseからユーザー情報を取得
        response = supabase.table("users").select("*").eq("username", login_data.username).execute()
        
        # デバッグ用（本番では削除）
        print(f"Username: {login_data.username}")
        print(f"Password: {login_data.password}")
        print(f"Response: {response.data}")
        
        # ユーザーが存在しない場合
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ユーザー名またはパスワードが間違っています"
            )
        
        user = response.data[0]
        
        # パスワードの確認
        if user["password"] != login_data.password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ユーザー名またはパスワードが間違っています"
            )
        
        # 認証成功
        return LoginResponse(
            success=True,
            message=f"ようこそ！{user['username']}さん",
            user_id=user["id"]
        )
        
    except HTTPException:
        # HTTPExceptionはそのまま再発生
        raise
    except Exception as e:
        # その他のエラー
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サーバーエラーが発生しました"
        )

# ヘルスチェックエンドポイント
@app.get("/health")
async def health_check():
    try:
        # Supabaseへの接続テスト
        response = supabase.table("users").select("count", count="exact").execute()
        return {
            "status": "healthy",
            "database": "connected",
            "users_count": response.count
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }

if __name__ == "__main__":
    # 環境変数からポートとホストを取得（デフォルト値を設定）
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    
    uvicorn.run(app, host=host, port=port)