# 우아주유소 (wooajuyuso.wooahouse.com)

고속도로 주유소 226곳 유가(한국도로공사 OpenAPI `curStateStation`, key=test) 노선·정유사·순위 사이트. GitHub Actions가 매일 KST 06:30에 `scripts/fetch_highway.py`로 가격을 받아 빌드·배포한다(커밋 없음, 실패 시 커밋된 data/highway.json 사용).

- 확장 계획: 오피넷 무료 API(인증키 하루 300건 제한) 기반 시군구별 최저가 TOP10·시도 평균가. 수집 상태는 data/opinet.json 에 누적(미구현).
- 빌드: `python scripts/build_site.py`
