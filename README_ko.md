# OpenHull

[![ci](https://github.com/5777-wq/OpenHull/actions/workflows/ci.yml/badge.svg)](https://github.com/5777-wq/OpenHull/actions/workflows/ci.yml)

[English](README.md) | [简体中文](README_zh.md) | [日本語](README_ja.md) | **한국어** | [Deutsch](README_de.md) | [Français](README_fr.md) | [Español](README_es.md) | [Italiano](README_it.md) | [Português](README_pt.md) | [Русский](README_ru.md)

> Design the shell that carries it all.

AI 에이전트가 오케스트레이션하는 오픈소스 파라메트릭 선박 초기설계
툴체인.

작업 지시서(선종, 재화중량, 서비스 속도, 항해 해역)를 입력하면
에이전트 파이프라인이 주요 치수, 정수 성능, 선형도, 저항/추진/복원성
평가, 도면 출력(DXF)을 자동으로 생성합니다.

## 현재 상태

**v0.1 출시** — 1단계 완료: 태스크북 기반 중량·부력 평형, 주요치, 정수력, 초동복원성·트림, 건현 검사 — 모두 JBC 기준선으로 검증 완료([VALIDATION.md](VALIDATION.md) 참조). 실행: `openhull run examples/taskbook_bulk_carrier.yaml`.

## 로드맵

- [x] 스테이지 1 — 주요 치수 반복 및 정수 성능 계산 코어 (**v0.1**)
- [ ] 스테이지 2 — 파라메트릭 선형 생성(모선 변환)
- [ ] 스테이지 3 — 성능 루프: 저항 / 추진 / 복원성
- [ ] 스테이지 4 — 도면 출력(DXF) 및 설계 보고서
- [ ] 스테이지 5 — 문서화 및 커뮤니티 릴리스 (v1.0)

## 설계 원칙

1. 모든 출력은 수식 또는 공개 문헌으로 소급 검증 가능해야 합니다
2. 새 기능 추가보다 공개 벤치마크 선박 데이터 검증을 우선합니다
3. 경험식은 적용 범위를 명시하고, 범위를 벗어난 입력은 거부합니다
4. 수식으로 쓸 수 있는 것은 자동화하고, 쓸 수 없는 것은 엔지니어에게 맡깁니다

## 라이선스

[MIT](LICENSE)
