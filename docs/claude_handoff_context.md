# EnzyFlow AI - Claude Web版への引き継ぎドキュメント

## プロジェクト概要

**EnzyFlow AI** は、バイオマス分解酵素の発見・最適化シミュレーターです。
セルロース系バイオマス（稲わら、バガス等）から糖を生産する酵素カクテルの設計を支援します。

### 現在の技術スタック
- **フロントエンド**: Streamlit
- **酵素埋め込み**: ESM-2 (facebook/esm2_t6_8M_UR50D, 320次元)
- **機械学習**: Gaussian Process Regression (収率予測)
- **反応シミュレーション**: Tellurium/Roadrunner (Michaelis-Menten速度論)
- **最適化**: Bayesian Optimization (Active Learning)

---

## 現在のシステム構成

```
src/
├── ai_model/
│   ├── design_engine.py    # ESM-2埋め込み、変異提案、Active Learning
│   ├── screening.py        # vHTSスコアリング (kcat/Km ベース)
│   └── train_yield_predictor.py
├── analytics/
│   └── app.py              # Streamlit UI (3タブ構成)
├── data_engineering/
│   ├── generate_features.py  # ESM-2埋め込み生成
│   ├── populate_kinetics.py  # バイオフィジカルオラクル
│   └── dataset_manager.py
├── validation/
│   └── validator.py        # 反応速度論シミュレーション
└── resources/
    └── materials.py        # バイオマス組成データ
```

---

## 完了済みの改善

### v1 → v4 の進化

| バージョン | 主な改善 |
|------------|----------|
| v1 | 基本的なMichaelis-Menten、ランダム埋め込み |
| v2 | ESM-2実装、マルチ酵素モデル (EG→BG) |
| v3 | UI刷新、フィードバックループ |
| v4 | **kcat/Km スコアリング、Time to 80% 指標** |

### 最新の指標システム

- **Tab 1 (vHTS)**: 触媒効率 (kcat/Km) ベースのEfficiency Score
- **Tab 2 (Design)**: 相対改善率 (%) = (Mutant - WT) / WT × 100
- **Tab 3 (Verification)**: **Time to 80%** と **Time Reduction (%)** が主要KPI

収率飽和問題（上位酵素がすべて99%に到達）を解決するため、「どれだけ速く80%に到達するか」を評価指標に変更しました。

---

## 現在の課題：前処理が未モデル化

### 問題点

現在のシミュレーターは以下を**暗黙的に仮定**しています：
- リグニン: 0%（実際は20-30%）
- 酵素アクセシビリティ: 100%（実際は10-40%）
- 阻害物質 (HMF, フルフラール): 0%

これは「理想的に前処理されたセルロース (Avicel)」を前提としており、実際のバイオマスとは大きく乖離します。

### 化学的前処理の種類と影響

| 前処理法 | アクセシビリティ | 主な阻害物質 |
|----------|------------------|--------------|
| 希硫酸 | 40-60% | HMF, フルフラール |
| アルカリ | 50-70% | フェノール類 |
| 蒸気爆砕 | 45-65% | 有機酸 |
| なし | 5-15% | なし |

---

## 次のステップ：2つのアプローチ

### アプローチ1: 並行複発酵シミュレーター（推奨・優先）

**コンセプト**: 日本酒の並行複発酵をモデルに、阻害物質を消費する微生物との共培養を最適化

```
日本酒モデル:
  麹菌(糖化) + 酵母(発酵) + 乳酸菌(環境制御)

セルロース分解モデル:
  セルラーゼ(糖化) + 発酵菌(エタノール生産) + 阻害物質分解菌(HMF/フルフラール除去)
```

**実装ステップ**:
1. 阻害物質の生成・影響モデルを `validator.py` に追加
2. 阻害物質分解菌の成長・消費モデルを追加
3. 微生物コンソーシアムのバランス最適化UI

### アプローチ2: スーパー酵素探索

**コンセプト**: 化学的前処理なしで機能する、リグニン耐性・阻害物質耐性の酵素を探索

**必要な特性**:
- リグニン非生産的吸着の回避
- HMF/フルフラール存在下での活性維持
- 高結晶性セルロースへの攻撃力

**実装ステップ**:
1. 耐性酵素のESM-2埋め込みを収集
2. 耐性/非耐性の分類器を訓練
3. Active Learningで耐性変異を優先探索

---

## Phase 1 実装案：阻害物質モデル

### 拡張する反応モデル (Antimony形式)

```python
model InhibitorAwareSaccharification
    species S, C2, G, I_HMF, I_Fur, L;

    # 初期条件
    S = {substrate_conc};      # セルロース
    L = {lignin_conc};         # リグニン
    I_HMF = {initial_hmf};     # 前処理由来のHMF
    I_Fur = {initial_fur};     # 前処理由来のフルフラール

    # パラメータ
    Ki_HMF = 5.0;    # HMF阻害定数 (mM)
    Ki_Fur = 3.0;    # フルフラール阻害定数 (mM)
    K_lignin = 10.0; # リグニン吸着定数

    # 有効酵素濃度（リグニン吸着考慮）
    E_free := E_total / (1 + L / K_lignin);

    # 阻害因子
    inhibition := 1 / (1 + I_HMF/Ki_HMF + I_Fur/Ki_Fur);

    # 糖化反応
    J1: S -> C2; kcat_EG * E_free * S * inhibition / (Km_EG * (1 + C2/Ki_C2) + S);
    J2: C2 -> G; kcat_BG * E_BG * C2 * inhibition / (Km_BG * (1 + G/Ki_G) + C2);
end
```

### Phase 2: 並行複発酵モデル

```python
model ParallelCoFermentation
    species G, EtOH, I_HMF, X_yeast, X_detox;

    # 微生物濃度
    X_yeast = 0.1;   # 酵母 (g/L)
    X_detox = 0.05;  # 阻害物質分解菌 (g/L)

    # パラメータ
    mu_max_yeast = 0.3;   # 酵母最大比増殖速度 (1/h)
    mu_max_detox = 0.15;  # 分解菌最大比増殖速度 (1/h)
    Ks_G = 1.0;           # 酵母のグルコース親和性 (g/L)
    Ks_HMF = 0.5;         # 分解菌のHMF親和性 (mM)
    Ki_yeast_HMF = 2.0;   # 酵母へのHMF阻害定数 (mM)

    # 酵母成長・発酵（HMF阻害あり）
    mu_yeast := mu_max_yeast * G / (Ks_G + G) * (1 - I_HMF / Ki_yeast_HMF);
    J_yeast_growth: -> X_yeast; mu_yeast * X_yeast;
    J_fermentation: G -> EtOH; mu_yeast * X_yeast * Y_etoh;

    # 阻害物質分解菌の成長（HMF消費）
    mu_detox := mu_max_detox * I_HMF / (Ks_HMF + I_HMF);
    J_detox_growth: -> X_detox; mu_detox * X_detox;
    J_hmf_consumption: I_HMF -> ; mu_detox * X_detox / Y_hmf;
end
```

---

## データベース情報

### 酵素データ
- **ファイル**: `data/processed/enzyme_kinetics.csv`
- **レコード数**: 100酵素
- **カラム**: id, kcat, Km, Ki, t_opt, ph_opt, organism, sequence, source_type

### 埋め込みデータ
- **ファイル**: `data/processed/enzyme_features.csv`
- **次元数**: 320 (ESM-2)

### バイオマスデータ
- **ファイル**: `src/resources/materials.py`
- **対応基質**: Rice Straw, Coffee Beans (Spent), Sugarcane Bagasse

---

## 議論の経緯サマリー

1. **初期レビュー**: ランダム埋め込み、人工オラクル関数を指摘 → ESM-2実装
2. **UI改善**: 基質選択機能の復活、指標の動的化
3. **ループ問題**: `_v1_AI`酵素がDesignEngineで認識されない → `custom_dataframe`注入で解決
4. **収率飽和問題**: Yield 99%で差が見えない → **Time to 80%** 指標に変更
5. **前処理問題**: リグニン・阻害物質が未考慮 → **並行複発酵アプローチ**を提案

---

## 次のアクション

Claude Web版では以下を進めてください：

### 優先度: 高
1. **阻害物質モデルの詳細設計**
   - HMF/フルフラールの阻害カイネティクス
   - リグニン吸着モデル
   - 前処理条件と阻害物質濃度の関係

2. **並行複発酵の微生物候補リスト**
   - HMF分解菌: *Cupriavidus basilensis*, *Pseudomonas putida*
   - フェノール分解菌: *Rhodococcus opacus*
   - 各微生物のカイネティクスパラメータ

### 優先度: 中
3. **スーパー酵素探索の戦略**
   - 既知の耐性酵素のデータ収集元 (BRENDA, UniProt)
   - 耐性特徴量の定義

---

## 参考文献・データソース

- **BRENDA**: https://www.brenda-enzymes.org/
- **CAZy**: http://www.cazy.org/ (糖質関連酵素データベース)
- **NREL**: バイオマス組成データ
- **ESM-2**: https://github.com/facebookresearch/esm

---

*このドキュメントは Claude Code から Claude Web への引き継ぎ用に作成されました。*
*最終更新: 2026-01-30*
