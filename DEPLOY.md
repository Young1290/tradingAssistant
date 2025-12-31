# 快速部署指南

## 🚀 部署步骤

### 1. 推送到 GitHub
```bash
cd /Users/user/tradingAssistant
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/Young1290/tradingAssistant.git
git push -u origin main
```

### 2. 部署 Backend 到 Render
1. 访问 https://render.com
2. New + → Web Service
3. Connect GitHub repo
4. 配置:
   - Root Directory: `backend`
   - Runtime: Docker
5. 环境变量:
   ```
   GEMINI_API_KEY=your_key
   CRYPTOQUANT_API_KEY=your_key (可选)
   ```
6. Create Web Service

7. 获取 Deploy Hook:
   - Settings → Deploy Hook → 复制 URL
   - 在 GitHub Settings → Secrets → 添加:
     ```
     RENDER_DEPLOY_HOOK_URL=https://api.render.com/deploy/srv-xxx
     ```

### 3. 部署 Frontend 到 Vercel
1. 访问 https://vercel.com
2. Import GitHub repo
3. Root Directory: `frontend`
4. 环境变量:
   ```
   VITE_API_URL=https://your-backend.onrender.com
   ```
5. Deploy

6. 更新 `vercel.json`:
   - 替换 `YOUR_BACKEND_URL` 为实际 Render URL

### 4. 完成！
每次 push 到 `main` 分支，backend 会自动重新部署。

## 📝 需要的文件
- ✅ `.github/workflows/deploy.yml`
- ✅ `vercel.json`
- ✅ `tradingAssistant/backend/requirements.txt`
- ✅ `tradingAssistant/backend/.env.example`
