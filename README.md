# Middle East Daily Brief — 中东每日简报

## 一键运行

双击 `启动仪表盘.bat` 即可：
1. 自动抓取 13 个中东媒体源
2. 生成四栏日报 HTML（报纸风格）
3. 在浏览器中自动打开

或者在命令行运行：
```bash
cd "d:\Boeker 1.0\middle-east-dashboard"
python main.py --fetch        # 抓取 + 生成
python main.py --serve        # 启动 HTTP 服务
```

## 日报格式

四栏报纸布局：政治 | 外交 | 经济 | 军事冲突

输出为完全自包含的单个 HTML 文件（零外部依赖），
在 `output/index.html`，可直接用浏览器打开或发送给他人。

## 数据来源覆盖 (13 个网站)

| 网站 | 获取方式 | 语言 |
|------|---------|------|
| Al Arabiya | RSS | EN/AR |
| Al Jazeera | RSS + Scraper | EN/AR |
| Youm7 | Scraper (首页抓取) | AR |
| SANA | RSS | AR |
| Al Riyadh | RSS | AR |
| Ahram Gate | Scraper (英文版) | EN |
| AA (Anadolu) | RSS × 2 | EN/AR |
| Reuters | Scraper | EN |
| Arab News | RSS | EN |
| Egypt Independent | Scraper | EN |
| SPA | Scraper (Next.js JSON) | EN/AR |
| Al Araby / New Arab | RSS | EN/AR |
| Al Jazeera English | Scraper 备用 | EN |

## 系统要求

- Python 3.10+
- `pip install feedparser jinja2`
