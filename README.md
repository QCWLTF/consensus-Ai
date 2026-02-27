# Consensus AI: 논문 분석을 위한 다중 AI 교차 검증

공대 대학원생을 위한 논문 분석 프로토타입. PDF 업로드 또는 텍스트 입력 후, 여러 AI(GPT, Gemini, Perplexity, Claude)가 토의하여 최적의 분석 결과를 제안합니다.

## 지원 AI

- **GPT (OpenAI)** - gpt-4o
- **Gemini (Google)** - gemini-2.0-flash
- **Perplexity** - sonar-pro
- **Claude (Anthropic)** - claude-sonnet-4-6

## 주요 기능

- PDF 업로드로 논문 텍스트 자동 추출
- 일반 모드(단순 종합) / 심층 토론 모드(상호 비판)
- 보유한 API 키만으로 선택적 사용

## 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

브라우저에서 http://localhost:8501 접속

## 환경 변수 (선택)

API 키는 앱 내 사이드바에서 입력하거나, 배포 시 환경 변수로 설정할 수 있습니다.
