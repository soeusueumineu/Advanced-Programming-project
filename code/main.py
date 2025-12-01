import json, os, math, re, sys, platform
from datetime import datetime

# 전역 플래그

SHOW_PLOTS = True   # 그래프 팝업 표시
SAVE_PLOTS = True   # PNG 저장

# 기본 설정값

DEFAULT_CONFIG = {
    "tax": {
        "dividend_rate": 0.154,   # 배당소득세(예: 15.4%)
        "capital_gain_rate": 0.22 # 양도소득세(예: 22%)
    },
    "allocation_classic": {
        "보수형": {"주식": 0.30, "채권": 0.60, "현금": 0.10},
        "중립형": {"주식": 0.60, "채권": 0.35, "현금": 0.05},
        "공격형": {"주식": 0.85, "채권": 0.10, "현금": 0.05}
    },
    "research_portfolios": {
        "보수형": {
            "배당주 (미국배당)": {"비중": 0.30, "예시": ["TIGER 미국배당다우존스", "VIG", "SCHD"]},
            "종합채권": {"비중": 0.60, "예시": ["BND", "AGG", "TIGER 미국채권혼합"]},
            "단기자산": {"비중": 0.10, "예시": ["MMF/예금", "단기채(SHV, BIL)"]}
        },
        "중립형": {
            "미국성장 + S&P500": {"비중": 0.60, "예시": ["VOO", "QQQM/나스닥100", "KODEX/TIGER 나스닥100"]},
            "종합채권": {"비중": 0.35, "예시": ["BND", "AGG"]},
            "단기자산": {"비중": 0.05, "예시": ["MMF/예금"]}
        },
        "공격형": {
            "성장주 (나스닥 중심)": {"비중": 0.85, "예시": ["QQQM", "TIGER 미국나스닥100", "SCHG"]},
            "완충채권": {"비중": 0.10, "예시": ["BND", "AGG"]},
            "현금": {"비중": 0.05, "예시": ["MMF/예금"]}
        }
    }
}

CONFIG_PATH = os.path.join("config", "config.json")
OUTPUT_DIR = "output"

# UTILITIES

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

def slugify(text):
    s = re.sub(r"[^\w\-가-힣]+", "_", text).strip("_")
    return s[:60] if s else "goal"

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_CONFIG

def pct(x): return f"{x*100:.1f}%"

def won(x):
    try:
        return f"{round(x):,}원"
    except Exception:
        return f"{x:,}원"

def line(): print("-"*70)

def input_int(msg, min_val=None):
    while True:
        val = input(msg).strip().replace(",", "")
        try:
            v = int(val)
            if min_val is not None and v < min_val:
                print(f"{min_val} 이상을 입력하세요.")
                continue
            return v
        except ValueError:
            print("숫자로 입력하세요.")

def input_float(msg, min_val=None, max_val=None):
    while True:
        val = input(msg).strip().replace(",", "").replace("%", "")
        try:
            if val == "":
                return 0.0
            v = float(val)
            if v > 1.0:  # "5" → 0.05
                v = v / 100.0
            if min_val is not None and v < min_val:
                print(f"{min_val} 이상 입력.")
                continue
            if max_val is not None and v > max_val:
                print(f"{max_val} 이하 입력.")
                continue
            return v
        except ValueError:
            print("숫자(또는 %)로 입력하세요. 예: 5 또는 0.05 또는 1,000,000")

def input_choice(msg, choices, default=None):
    opts = "/".join(choices)
    while True:
        s = input(f"{msg} ({opts})" + (f" [기본:{default}] " if default else " ")).strip()
        if not s and default:
            return default
        if s in choices:
            return s
        print("목록 중에서 선택하세요.")

def input_text(msg, allow_empty=False):
    while True:
        s = input(msg).strip()
        if s or allow_empty:
            return s
        print("값을 입력하세요.")

# Matplotlib 보조 (폰트/백엔드/표시)

def prefer_gui_backend():
    try:
        import matplotlib

        current = matplotlib.get_backend().lower()
        if any(k in current for k in ["macosx", "tkagg", "qt5agg", "qtagg"]):
            return matplotlib.get_backend()
        candidates = []
        if platform.system() == "Darwin":
            candidates.append("MacOSX")
        candidates += ["TkAgg", "Qt5Agg", "QtAgg"]
        for b in candidates:
            try:
                matplotlib.use(b, force=True)
                return b
            except Exception:
                continue
        return None
    except Exception:
        return None

def setup_korean_font():
    try:
        import matplotlib
        from matplotlib import font_manager as fm
        candidates = [
            "AppleGothic", "Malgun Gothic", "NanumGothic",
            "Noto Sans CJK KR", "NanumBarunGothic",
        ]
        available = set(f.name for f in fm.fontManager.ttflist)
        for name in candidates:
            if name in available:
                matplotlib.rcParams["font.family"] = name
                matplotlib.rcParams["axes.unicode_minus"] = False
                return name
        matplotlib.rcParams["axes.unicode_minus"] = False
        return None
    except Exception:
        return None

def show_or_save(fig, outfile_png, title_for_log="그래프"):
    try:
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"matplotlib을 사용할 수 없어 {title_for_log} 생성을 건너뜁니다.", e)
        return None

    saved_path = None
    if SAVE_PLOTS and outfile_png:
        try:
            ensure_dir(os.path.dirname(outfile_png))
            fig.savefig(outfile_png, dpi=150)
            saved_path = outfile_png
        except Exception as e:
            print(f"{title_for_log} 파일 저장 실패: {e}")

    if SHOW_PLOTS:
        try:
            prefer_gui_backend()  # 가능한 경우 GUI로 스위칭
            plt.show(block=True)
        except Exception as e:
            if saved_path:
                print(f"그래프 팝업 표시 실패. 파일로 저장만 했습니다: {saved_path}")
            else:
                print("그래프 팝업 표시 실패 및 파일 저장도 되지 않았습니다.", e)

    try:
        import matplotlib.pyplot as plt
        plt.close(fig)
    except Exception:
        pass

    return saved_path


# RISK PROFILE (설문 + 나이보정)

RISK_TO_SCORE = {"보수형": 1.0, "중립형": 2.0, "공격형": 3.0}
SCORE_TO_RISK = {1: "보수형", 2: "중립형", 3: "공격형"}

def base_risk_from_age(age):
    if age < 30: return "공격형"
    if age < 60: return "중립형"
    return "보수형"

def age_tilt(score, age):
    if age < 30: score += 0.5
    elif age < 45: score += 0.25
    elif age < 60: score += 0.0
    elif age < 70: score -= 0.25
    else: score -= 0.5
    return max(1.0, min(3.0, score))

def decide_risk(selected, age):
    base = base_risk_from_age(age) if selected == "자동" else selected
    base_score = RISK_TO_SCORE[base]
    tilted = age_tilt(base_score, age)
    final = SCORE_TO_RISK[int(round(tilted))]
    desc = f"(기본={base}:{base_score:.2f} → 나이보정={tilted:.2f} → 최종={final})"
    return final, desc

def ask_risk_questions():
    print("\n[📊 투자 성향 진단 테스트]")
    print("간단한 5가지 질문을 통해 투자 성향을 판단합니다.")
    print("각 질문에 대해 자신의 생각과 가장 가까운 번호를 입력하세요.\n")

    total = 0
    q_list = [
        ("1️⃣ 투자 시 손실이 발생하면 어떻게 하시겠습니까?",
         ["① 바로 매도해 손실을 줄인다 (1점)",
          "② 조금 기다려 본다 (2점)",
          "③ 오히려 추가매수로 평균단가를 낮춘다 (3점)"]),
        ("2️⃣ 투자 기간은 주로 얼마나 계획하십니까?",
         ["① 1년 이하 (1점)", "② 1~3년 (2점)", "③ 3년 이상 (3점)"]),
        ("3️⃣ 수익률과 위험 중 어느 쪽을 더 중시하십니까?",
         ["① 손실이 적은 것이 중요 (1점)", "② 균형 (2점)", "③ 고수익 위해 위험 감수 (3점)"]),
        ("4️⃣ 포트폴리오 비중 선호는?",
         ["① 채권/예금 위주 (1점)", "② 주식·채권 균형 (2점)", "③ 주식 중심 (3점)"]),
        ("5️⃣ 투자 경험은?",
         ["① 거의 없음 (1점)", "② 보통 (2점)", "③ 다양 (3점)"]),
    ]

    for q, opts in q_list:
        print(f"\n{q}")
        for o in opts: print(o)
        while True:
            ans = input("선택 (1~3): ").strip()
            if ans in {"1","2","3"}:
                total += int(ans); break
            print("1~3 중 하나를 입력하세요.")

    avg = total / len(q_list)
    if avg < 1.7: risk = "보수형"
    elif avg < 2.4: risk = "중립형"
    else: risk = "공격형"

    print(f"\n👉 설문 결과: {risk} (평균점수 {avg:.2f})")
    return risk

# PORTFOLIO (구체 비중 추천 + 파이 차트 팝업)

RECOMMENDATION_MODELS = {
    "공격형": {
        "금": {"weight": 0.05, "examples": ["IAU", "GLD", "금현물"]},
        "배당주": {"weight": 0.10, "examples": ["VIG", "SCHD", "TIGER 미국배당다우존스"]},
        "S&P500": {"weight": 0.20, "examples": ["VOO", "SPY", "TIGER 미국S&P500"]},
        "나스닥100": {"weight": 0.50, "examples": ["QQQM", "QQQ", "TIGER 미국나스닥100"]},
        "채권(종합/완충)": {"weight": 0.10, "examples": ["BND", "AGG"]},
        "현금": {"weight": 0.05, "examples": ["MMF/예금"]}
    },
    "중립형": {
        "금": {"weight": 0.05, "examples": ["IAU", "GLD", "금현물"]},
        "배당주": {"weight": 0.15, "examples": ["VIG", "SCHD", "TIGER 미국배당다우존스"]},
        "S&P500": {"weight": 0.30, "examples": ["VOO", "SPY", "TIGER 미국S&P500"]},
        "나스닥100": {"weight": 0.30, "examples": ["QQQM", "QQQ", "TIGER 미국나스닥100"]},
        "채권(종합/완충)": {"weight": 0.15, "examples": ["BND", "AGG"]},
        "현금": {"weight": 0.05, "examples": ["MMF/예금"]}
    },
    "보수형": {
        "금": {"weight": 0.05, "examples": ["IAU", "GLD", "금현물"]},
        "배당주": {"weight": 0.25, "examples": ["VIG", "SCHD", "TIGER 미국배당다우존스"]},
        "S&P500": {"weight": 0.20, "examples": ["VOO", "SPY", "TIGER 미국S&P500"]},
        "나스닥100": {"weight": 0.10, "examples": ["QQQM", "QQQ", "TIGER 미국나스닥100"]},
        "채권(종합/완충)": {"weight": 0.35, "examples": ["BND", "AGG"]},
        "현금": {"weight": 0.05, "examples": ["MMF/예금"]}
    },
}

def plot_portfolio_pie(risk_name, model, amount, outfile_png):
    try:
        import matplotlib.pyplot as plt
    except Exception as e:
        print("matplotlib을 사용할 수 없어 포트폴리오 원형 그래프 생성을 건너뜁니다.", e)
        return None

    setup_korean_font()
    labels = list(model.keys())
    weights = [model[k]["weight"] for k in labels]

    fig = plt.figure(figsize=(6.2, 6.2))
    plt.pie(
        weights,
        labels=labels,
        autopct=lambda p: f"{p:.1f}%",
        startangle=90,
        wedgeprops=dict(edgecolor="white", linewidth=1)
    )
    plt.title(f"[{risk_name}] 포트폴리오 비중", pad=14)
    plt.tight_layout()

    return show_or_save(fig, outfile_png, title_for_log="포트폴리오 원형 그래프")

# ---------- 목표 시뮬 그래프 (팝업) ----------
def plot_progress(goal_name, months_axis, principal_arr, balance_arr, target, outfile_png):
    try:
        import matplotlib.pyplot as plt
    except Exception as e:
        print("matplotlib을 사용할 수 없어 목표 그래프 생성을 건너뜁니다.", e)
        return None

    setup_korean_font()
    # 만원 단위 스케일
    p_m = [x/10000.0 for x in principal_arr]
    b_m = [x/10000.0 for x in balance_arr]
    tgt_m = target/10000.0

    fig = plt.figure(figsize=(10, 5.5))
    plt.plot(months_axis, p_m, label="누적 원금", linewidth=2)
    plt.plot(months_axis, b_m, label="평가액(수익 반영)", linewidth=2)
    plt.axhline(y=tgt_m, linestyle="--", linewidth=1.5, label="목표 금액(만원)")
    plt.title(f"[{goal_name}] 누적 원금 vs 평가액", pad=12)
    plt.xlabel("투자 기간 (월)")
    plt.ylabel("금액 (만원)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    return show_or_save(fig, outfile_png, title_for_log="목표 진행 그래프")

# GOAL SIMULATOR (그래프 + 연도별/달성시점 텍스트 출력)

def simulate_with_initial_and_monthly(pv, pmt, annual_return, years, target):
    months = years * 12
    r = annual_return / 12.0
    balance = float(pv)
    yearly, balances_monthly, principal_monthly = [], [], []
    reach_month = None
    cum_principal = float(pv)

    for m in range(1, months + 1):
        balance = balance * (1 + r) + pmt
        cum_principal += pmt
        balances_monthly.append(balance)
        principal_monthly.append(cum_principal)
        if reach_month is None and balance >= target:
            reach_month = m
        if m % 12 == 0:
            yearly.append(balance)

    if reach_month is None:
        extra_balance, extra_m = balance, 0
        while extra_m < 1200 and extra_balance < target:
            extra_m += 1
            extra_balance = extra_balance * (1 + r) + pmt
        if extra_balance >= target:
            reach_month = months + extra_m

    return {
        "yearly": yearly,
        "final_value": balance,
        "reach_month": reach_month,
        "balances_monthly": balances_monthly,
        "principal_monthly": principal_monthly,
    }

def format_months_to_ym(m):
    if m is None: return "달성 불가"
    y = (m - 1) // 12
    mm = ((m - 1) % 12) + 1
    return f"{y}년 {mm}개월" if y > 0 else f"{mm}개월"

# TAX

def calculate_tax(cfg):
    print("\n[세금 계산 도우미]")
    t = input_choice("계산 종류를 선택하세요", ["배당", "양도"], "배당")
    if t == "배당":
        gross = input_int("총 배당금(원): ", 0)
        rate = cfg["tax"]["dividend_rate"]
        tax = round(gross * rate)
        net = gross - tax
        line()
        print(f"총배당 {won(gross)} / 세율 {rate*100:.1f}%")
        print(f"예상 세금: {won(tax)} | 세후 금액: {won(net)}")
        line()
    else:
        buy = input_int("매수가(원): ")
        sell = input_int("매도가(원): ")
        qty = input_int("수량: ", 1)
        rate = cfg["tax"]["capital_gain_rate"]
        profit = (sell - buy) * qty
        tax = round(max(0, profit) * rate)
        net = profit - tax
        line()
        print(f"매수 {buy:,} / 매도 {sell:,} / 수량 {qty}")
        print(f"총차익: {won(profit)} | 세금: {won(tax)} | 세후 수익: {won(net)}")
        line()

# PORTFOLIO/GOAL

def show_portfolio(cfg):
    print("\n[포트폴리오 추천]")
    age = input_int("나이를 입력하세요 (예: 25): ", 10)
    survey_risk = ask_risk_questions()
    amount = input_int("투자 총액(원)을 입력하세요: ", 1)

    final_risk, desc = decide_risk(survey_risk, age)
    line(); print(f"최종 성향: {final_risk}  {desc}\n총 투자금: {amount:,}원"); line()

    model = RECOMMENDATION_MODELS[final_risk]
    print(f"{'자산/섹터':<14}{'비중':>8}{'금액':>16}   예시 ETF")
    line()
    for name, meta in model.items():
        w = meta["weight"]; ex = ", ".join(meta["examples"])
        print(f"{name:<14}{pct(w):>8}{won(amount*w):>16}   {ex}")
    line()

    ensure_dir(OUTPUT_DIR)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = f"portfolio_{slugify(final_risk)}_{stamp}"
    pie_path = os.path.join(OUTPUT_DIR, f"{base}.png")
    pie_out = plot_portfolio_pie(final_risk, model, amount, pie_path)
    if pie_out:
        print("시각화 파일:")
        print(f"- 포트폴리오 비중 원 그래프: {pie_out}")
    else:
        print("시각화 파일: (생성되지 않음)")
    line()

    if final_risk == "공격형":
        print("코멘트: 성장자산(나스닥100·S&P500) 중심, 금/채권/현금으로 변동성 완충.")
    elif final_risk == "보수형":
        print("코멘트: 배당·채권 비중을 높여 변동성 축소, 금·현금으로 방어력 보강.")
    else:
        print("코멘트: 성장성과 안정성 균형. 주식(나스닥·S&P500)과 채권, 배당, 금을 혼합.")

def goal_simulator():
    print("\n[🎯 목표 달성 시뮬레이터 (그래프 + 텍스트 요약)]")
    goal_name = input_text("목표 이름 (예: 내 집 마련, 은퇴자금, 여행 자금 등): ")
    target = input_int("목표 금액(원, 예: 100,000,000): ", 1)
    years  = input_int("목표 기간(년, 예: 10): ", 1)
    pv     = input_int("현재 보유 자산(원, 예: 10,000,000): ", 0)
    pmt    = input_int("월 투자 금액(원, 예: 300,000): ", 0)
    annual_rate = input_float("예상 연 수익률 (예: 5 또는 0.05 또는 5%): ", 0.0)

    result = simulate_with_initial_and_monthly(
        pv=pv, pmt=pmt, annual_return=annual_rate, years=years, target=target
    )

    months_axis = list(range(1, years*12 + 1))
    reach_m = result["reach_month"]
    reach_text = format_months_to_ym(reach_m)
    within_period = (reach_m is not None and reach_m <= years*12)

    # ----- 텍스트 요약 출력 -----
    line()
    print(f"목표: {goal_name}")
    print(f"- 목표 금액: {won(target)}")
    print(f"- 목표 기간: {years}년")
    print(f"- 현재 보유 자산: {won(pv)}")
    print(f"- 월 투자 금액: {won(pmt)}")
    print(f"- 예상 연 수익률: {annual_rate*100:.2f}%")
    line()

    status_txt = "기간 내 달성 가능 ✅" if within_period else "기간 내 달성 불가 ❌"
    print(f"▶ 목표 달성 예상 시점: {reach_text} ({status_txt})")
    if not within_period:
        period_end_value = result['balances_monthly'][-1] if result['balances_monthly'] else 0.0
        shortage = max(0.0, target - period_end_value)
        print(f"▶ 기간 말 예상 평가액: {won(period_end_value)} (목표 대비 부족 {won(shortage)})")
    line()

    print("연도별 예상 평가액 (명목):")
    print(f"{'연차':>4}  {'평가액':>18}")
    line()
    for i, val in enumerate(result["yearly"], start=1):
        print(f"{i:>4}  {won(val):>18}")
    line()

    # ----- 그래프 저장 + 팝업 -----
    ensure_dir(OUTPUT_DIR)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = f"{slugify(goal_name)}_{stamp}"
    chart_path = os.path.join(OUTPUT_DIR, f"{base}_progress.png")

    chart_out = plot_progress(
        goal_name,
        months_axis,
        result["principal_monthly"],
        result["balances_monthly"],
        target,
        chart_path
    )
    if chart_out:
        print("시각화 결과 파일:")
        print(f"- 누적 원금 vs 평가액: {chart_out}")
    else:
        print("시각화 결과 파일: (생성되지 않음)")
    line()


# MAIN LOOP

def main():
    cfg = load_config()
    print("===== 💰 MyFinPlanner (포트폴리오 그래프 팝업 + 단순 세금계산 + 목표 그래프 팝업) =====")
    while True:
        print("\n메뉴: 1) 포트폴리오 추천  2) 세금 계산  3) 목표 시뮬레이터  4) 종료")
        sel = input_choice("메뉴를 선택하세요", ["1", "2", "3", "4"])
        if sel == "1":
            show_portfolio(cfg)
        elif sel == "2":
            calculate_tax(cfg)
        elif sel == "3":
            goal_simulator()
        elif sel == "4":
            print("프로그램을 종료합니다. 감사합니다!")
            break

if __name__ == "__main__":
    main()
