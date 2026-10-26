# 대한전선 DART Financial Agent

[![Dashboard](assets/dashboard-badge.svg)](https://hsc-class01.github.io/sjw_DH/)

## 🔗 대시보드 바로가기

[![Dashboard](assets/dashboard-badge.svg)](https://hsc-class01.github.io/sjw_DH/)

대한전선(001440)의 금융감독원 OpenDART 정기보고서 데이터를 자동 수집하고, 주요 재무수치 및 재무비율을 계산한 뒤 GitHub Pages 대시보드로 배포하는 데이터 에이전트입니다.

> **첨부파일 관련:** 현재 대화에서는 사용자가 언급한 재무수치 첨부파일이 실제로 전달되지 않아, 기본적인 핵심 재무제표 계정과 표준 재무비율을 포함했습니다. 첨부파일을 다시 업로드하면 `config.yaml`의 계정/비율 목록을 그 기준으로 맞추면 됩니다.

## 범위

- 대상: 대한전선 / 종목코드 `001440` / DART corp_code `00113207`
- 기간: 2010년부터 현재까지
- 보고서: 사업보고서, 반기보고서, 1분기보고서, 3분기보고서
- 2015년 이후: OpenDART 구조화 재무제표 API 우선 사용
- 2010~2014년: DART 공시검색 + 공시서류 원본파일 fallback parser
- 분석: 매출액, 영업이익, 순이익, 자산, 부채, 자본, 유동자산/부채, 현금흐름 및 성장성/수익성/안정성 지표
- 배포: GitHub Pages
- 자동화: GitHub Actions, 매월 1일 00:00 UTC (한국시간 09:00)

## API Key 설정

1. OpenDART에서 인증키를 발급합니다: https://opendart.fss.or.kr/
2. GitHub repository → **Settings → Secrets and variables → Actions → New repository secret**
3. Name: `DART_API_KEY`
4. Secret: 발급받은 40자리 인증키
5. 저장 후 **Actions → DART data update and GitHub Pages deploy → Run workflow**로 최초 실행

API key를 코드나 `config.yaml`에 직접 넣지 마세요.

## GitHub Pages 설정

Repository → **Settings → Pages**에서 Source를 **GitHub Actions**로 설정합니다. 이후 workflow가 `dashboard/`를 Pages artifact로 배포합니다.

### About 섹션 링크

Repository 오른쪽 **About → 톱니바퀴(Edit repository details)**에서 Website에 실제 GitHub Pages 주소를 입력하고 저장하세요. About 영역은 repository 파일만으로 안정적으로 설정할 수 없으므로 이 한 단계는 GitHub UI에서 설정하는 것이 안전합니다.

## 매월 1일 자동 업데이트

`.github/workflows/update-and-deploy.yml`의 cron은 다음과 같습니다.

```yaml
- cron: '0 0 1 * *'
```

GitHub Actions cron은 UTC 기준입니다. 따라서 한국시간(KST) 기준 매월 1일 오전 9시에 실행됩니다.

## Peer firms

국내 전선업 주요 비교기업으로 LS전선, 가온전선, 일진전기, 대원전선, LS에코에너지를 기본 구성했습니다. 연구자료에서도 LS전선·대한전선·가온전선·일진전기·대원전선 등이 국내 전선업 비교군으로 함께 다뤄집니다.

## 프로젝트 구조

```text
.
├── .github/workflows/update-and-deploy.yml
├── assets/dashboard-badge.svg
├── config.yaml
├── data/financials.csv
├── data/metadata.json
├── dashboard/index.html
├── requirements.txt
├── src/dart_agent.py
└── src/build_dashboard.py
```

## 주의사항

- OpenDART 구조화 재무제표 API는 2015년 이후 데이터를 제공합니다. 2010~2014년은 원문 fallback parser를 사용하도록 설계했습니다.
- 과거 보고서의 계정명/표 구조가 현재 XBRL 계정명과 다를 수 있어, 최초 historical backfill 실행 후 `data/financials.csv`의 결측값을 검수하는 것을 권장합니다.
- 연결재무제표(`CFS`)를 기본으로 수집합니다. 개별재무제표가 필요하면 `config.yaml`의 `fs_div`를 `OFS`로 변경하세요.
