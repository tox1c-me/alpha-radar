# -*- coding: utf-8 -*-
"""生成 2026-10-11 情报收集日报。"""
import io
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "reports", "daily-intel-2026-10-11.html")

CSS = """
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 40px 24px 72px;
    background: #f7f7f5; color: #2c2c2a;
    font-family: -apple-system, "Segoe UI", "Microsoft YaHei", system-ui, sans-serif;
    font-size: 16.5px; line-height: 1.75;
  }
  .wrap { max-width: 940px; margin: 0 auto; }
  header { margin-bottom: 26px; }
  h1 { font-size: 28px; font-weight: 600; margin: 0 0 8px; letter-spacing: .2px; }
  .date { color: #6b6a65; font-size: 14.5px; }
  .stats { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }
  .stat {
    background: #fff; border: 1px solid #e6e4de; border-radius: 9px;
    padding: 9px 14px; font-size: 14px; color: #575652;
  }
  .stat b { color: #2c2c2a; font-weight: 600; }
  .stat.final { border-color: #0f6e56; background: #f2faf7; }
  .stat.skip { border-color: #d8d6cf; background: #fafaf8; color: #86847e; }
  .funnel-note { font-size: 13.5px; color: #86847e; margin-top: 10px; }
  .mkt {
    display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px;
    font-size: 13.5px; font-family: ui-monospace, Consolas, monospace;
  }
  .mkt span { background: #fff; border: 1px solid #e6e4de; border-radius: 7px; padding: 6px 11px; color: #575652; }
  .up { color: #a32d2d; font-weight: 600; }
  .dn { color: #0f6e56; font-weight: 600; }
  section {
    background: #fff; border: 1px solid #e6e4de; border-radius: 14px;
    padding: 24px 28px 26px; margin-bottom: 18px;
  }
  section.l1 { border-left: 4px solid #993c1d; }
  section.l2 { border-left: 4px solid #185fa5; }
  section.l3 { border-left: 4px solid #854f0b; }
  section.l4 { border-left: 4px solid #a32d2d; }
  h2 { font-size: 19px; font-weight: 600; margin: 0 0 5px; }
  h3 { font-size: 16.5px; font-weight: 600; margin: 22px 0 8px; color: #575652; }
  .sub { font-size: 14.5px; color: #86847e; margin: 0 0 18px; }
  .item { padding: 15px 0; border-top: 1px solid #f0eee8; }
  .item:first-of-type { border-top: none; padding-top: 5px; }
  .meta { font-size: 14px; color: #86847e; margin-bottom: 5px; }
  .src { color: #575652; font-weight: 600; }
  .tag {
    display: inline-block; font-size: 12.5px; padding: 2px 8px; border-radius: 5px;
    margin-left: 8px; vertical-align: 2px;
  }
  .tag.hot { background: #fcebeb; color: #a32d2d; }
  .tag.warn { background: #faeeda; color: #854f0b; }
  .tag.new { background: #e1f5ee; color: #0f6e56; }
  /* 荧光笔标记：标在关键数字 / 一手源原话 / 可操作结论上 */
  .hl {
    background: #fff3a3; padding: 1px 3px; border-radius: 3px;
    box-decoration-break: clone; -webkit-box-decoration-break: clone;
  }
  .hl-key {
    background: #ffe066; padding: 1px 4px; border-radius: 3px;
    font-weight: 600;
    box-decoration-break: clone; -webkit-box-decoration-break: clone;
  }
  .body-text { margin: 0 0 7px; font-size: 16px; }
  .body-text code {
    font-family: ui-monospace, Consolas, monospace; font-size: 14px;
    background: #f4f2ec; padding: 1px 5px; border-radius: 4px; color: #854f0b;
    word-break: break-all;
  }
  a { color: #185fa5; text-decoration: none; }
  a:hover { text-decoration: underline; }
  .lnk { font-size: 13.5px; word-break: break-all; }
  table { width: 100%; border-collapse: collapse; font-size: 15px; margin-top: 8px; }
  th {
    text-align: left; font-weight: 600; font-size: 13.5px; color: #86847e;
    padding: 8px 10px 8px 0; border-bottom: 1px solid #e6e4de;
  }
  td { padding: 10px 10px 10px 0; border-bottom: 1px solid #f4f2ec; vertical-align: top; }
  td.cve { font-family: ui-monospace, Consolas, monospace; font-size: 13.5px; white-space: nowrap; color: #a32d2d; }
  td.date { white-space: nowrap; color: #86847e; font-size: 13.5px; }
  td.pkg { font-family: ui-monospace, Consolas, monospace; font-size: 13.5px; }
  td.pts { white-space: nowrap; font-family: ui-monospace, Consolas, monospace; font-size: 13.5px; color: #575652; }
  .sev {
    display: inline-block; font-size: 12px; padding: 2px 7px; border-radius: 4px;
    font-weight: 600; text-transform: uppercase;
  }
  .s-critical { background: #fcebeb; color: #a32d2d; }
  .s-high { background: #faeeda; color: #854f0b; }
  .s-medium { background: #eef4fb; color: #185fa5; }
  .s-low { background: #f0f0ee; color: #6b6a65; }
  footer { margin-top: 28px; font-size: 14.5px; color: #86847e; }
  footer ul { margin: 10px 0 0; padding-left: 20px; }
  footer li { margin-bottom: 6px; }
  .foot-log { margin-top: 8px; font-size: 13.5px; color: #a5a39c; }
  .foot-log code { font-family: ui-monospace, Consolas, monospace; font-size: 12.5px; }
  .note {
    background: #fff; border: 1px solid #e6e4de; border-left: 4px solid #185fa5;
    border-radius: 12px; padding: 18px 24px; margin-bottom: 18px; font-size: 15.5px;
  }
  .note b { font-weight: 600; }
  .note.ok { border-left-color: #0f6e56; background: #fbfefc; }
  .note.extra { border-left-color: #854f0b; }
  .note.warn { border-left-color: #a32d2d; background: #fffafa; }
  section.pv { border-left: 4px solid #0f6e56; }
  .pv-sub { font-size: 14.5px; color: #86847e; margin: 16px 0 6px; }
  .pv-table { margin-top: 2px; }
  .pv-when { white-space: nowrap; font-weight: 600; padding-right: 16px; }
  .pv-dim { color: #86847e; font-weight: 400; font-size: 13.5px; }
  .pv-urgent {
    background: #fcebeb; border: 1px solid #f0c6c6; border-radius: 9px;
    padding: 12px 15px; margin: 4px 0 6px; font-size: 15.5px; color: #a32d2d;
  }
"""

BODY = r"""
<header>
  <h1>情报收集 · 2026-10-11</h1>
  <div class="date">2026-10-11 星期日 · 覆盖窗口：北京时间 10-09 11:18 — 10-11 11:18（48 小时）</div>
  <div class="stats">
    <div class="stat">X 白名单 <b>15 / 15</b></div>
    <div class="stat">抓取合计 <b>103</b> 条</div>
    <div class="stat">窗口内相关 <b>38</b> 条</div>
    <div class="stat skip">上期已收录 <b>1</b> 条</div>
    <div class="stat">剔除 <b>24</b> 条</div>
    <div class="stat">进入筛选 <b>13</b> 条</div>
    <div class="stat final">最终收录 <b>13</b> 条</div>
    <div class="stat">L4 明细 <b>48</b> 条</div>
  </div>
  <div class="funnel-note">最终收录 <b>13</b> 条 = L1 6 + L2 1 + L3 6。X 白名单一手源 <b>15/15 全部成功</b>（经 Clash 轮换出口 IP，换节点 8 次），48 小时窗口内 <b>38</b> 条；其中 <b>1</b> 条为上期已收录、<b>24</b> 条按规则剔除，<b>13</b> 条进入正文筛选；外部源（CISA KEV / GitHub Advisory / Hacker News / Decrypt / Cointelegraph / The Block / Protos / CoinGecko）另产出 <b>9</b> 条正文素材。本期为<b>完整版</b>。</div>
  <div class="mkt">
    <span>BTC $82,907 <span class="up">+0.48%</span></span>
    <span>ETH $2,505.29 <span class="up">+0.58%</span></span>
    <span>BNB $747.03 <span class="up">+0.33%</span></span>
    <span>SOL $109.61 <span class="dn">-0.06%</span></span>
    <span>XRP $1.400 <span class="dn">-0.50%</span></span>
    <span>ZEC $1,228.85 <span class="up">+1.46%</span></span>
    <span>NEAR $5.23 <span class="up">+5.73%</span></span>
    <span>全球市值 $2.81T</span>
    <span>BTC 占比 59.1%</span>
  </div>
  <div class="funnel-note" style="margin-top:8px">文中<span class="hl">黄色荧光标记</span> = 本期关键数字 / 一手源原话 / 可操作结论；<span class="hl-key">深黄加粗</span> = 本期最该记住的那一条。</div>
</header>

<!-- PREVIEW-MODULE:BEGIN -->
<!-- PREVIEW-MODULE:END -->

<div class="note ok">
  <b>本期为完整版：X 白名单一手源 15/15 全部成功。</b>
  直连探测 <code>curl -m 8 https://x.com/aa_AFeng</code> → <b>000</b>（不通），改走 Clash 轮换通道（<code>x_profile_ssr.py --per-node 2 --hours 48</code>，经 <code>127.0.0.1:7897</code> 出口，实测 <code>-x http://127.0.0.1:7897 https://x.com/aa_AFeng</code> → <b>200</b>），<b>换节点 8 次，结束已自动恢复「🇺🇸美国 04 | 专线」</b>。15 个账号全部返回 200。
  <br><b>本期发现并修复两处环境变更</b>：
  <br>① <b>订阅整体更换</b> —— 原「寿司云」策略组已从 Clash 配置中消失，Clash API 对 <code>GET /proxies/寿司云</code> 返回 <b>404</b>，脚本在 <code>group_now()</code> 阶段即 traceback 退出（不是上两期的 400）。新机场为「<b>一元机场</b>」（Selector，20 个节点）。已把 <code>GROUP</code> 改为「一元机场」，并<b>逐节点实测</b>：18 个真实节点（港 01–04 / 日 01–10 / 美 01–04）访问 x.com <b>全部 200</b>（len≈157KB，无 TLS 重置），据此重建 <code>NODES</code> 白名单（港 01 / 日 01 / 美 01 / 日 05）。<b>若下期再遇 Clash API 4xx，先核对订阅是否又换机场。</b>
  <br>② <b>views 字段格式变更</b> —— SSR 流中已从 <code>views:{count:"N"}</code> 变为 <code>views:$R[n]={count:"N"}</code>，旧正则导致 12 条推文 views 全为 <code>None</code>。已修复为兼容两种形式（<code>views:(?:\$R\[\d+\]=\{)count:"(\d+)"</code>）。
  <br><b>原始 103 条 → 48 小时窗口内 38 条</b>，低于修复后常规区间（43–57）。已核查<b>非解析器回退</b>：解析锚点 <code>rest_id:"&lt;id&gt;",result:$R[n]={</code> 有效，抽查 ID / 时间 / 正文 / 互动数四项对齐；偏低的原因是<b>窗口内零产出账号多达 4 个</b> + 周末效应。
  <br><b>零窗口账号 4 个</b>：@SuperL9（最新 10-08 17:45）、@maid_crypto（最新 10-07 17:51）、@JieChao13754（最新停在 03-22，长期停更）、@machibigbrother（最新 10-09 01:20，刚好落在窗口外）——均属正常，非抓取失败。
  <br><b>引用链外部一手源</b>：@MagicalTux、@guanyuhan426、@AlanShao111、@gnn1948944、@predictdotfun、@4MBossChen、@BNBCHAIN（非白名单，来自引用链，收录时已标注）。<b>本期 Ledger 事件的关键技术细节（硬件植入模块实物图）正是由引用链外部源 @MagicalTux 提供</b>，再次验证修复后的解析器「抓引用链」是净增益。
</div>

<section class="l1">
  <h2>L1 必看</h2>
  <p class="sub">一手源原话 + 研究者 / 官方 / 平台级变化，最多 6 条</p>

  <div class="item">
    <div class="meta"><span class="src">X 外部一手源 @MagicalTux</span> + <span class="src">@guanyuhan426</span> + <span class="src">Protos</span> + <span class="src">The Block</span> · 10-09 23:42 — 10-11 10:05 北京时间 <span class="tag hot">本期最关键 · 硬件钱包信任危机（技术细节升级）</span></div>
    <p class="body-text"><b>Ledger 供应链攻击的作案手法被实物拆解曝光：攻击者把一块夹层模块塞进设备屏幕与原厂主板之间，模块集成 e-SIM + 可识别 Ledger 屏幕字体的 CPU + LTE 模块，<span class="hl-key">实时识别屏幕上显示的助记词并在识别完成后经 4G 外发</span>。</b></p>
    <p class="body-text">@MagicalTux（10-09 23:42，<b><span class="hl">1,102 赞 / 126 转发 / 103 万阅读</span></b>）直接贴出拆机图并标注三件套：「从左到右：e-SIM、能识别 Ledger 屏幕字体的固件 CPU（逐字捕获屏上出现的助记词）、以及助记词抓完后即可联网的 LTE 模块」。@guanyuhan426（10-10 00:36）用中文复述同一发现：「加了这么个模块夹在屏幕和原厂主板之间……当助记词识别并记录结束后通过 4G 模块把你的助记词发走」。Protos（10-10 00:40）与 The Block（10-09 22:52）确认被盗规模 <b><span class="hl">约 8,600 万美元</span></b>，源头指向东南亚经销商 CryptoBilis。</p>
    <p class="body-text"><b>白名单侧的两条反应同样值得记</b>：① @mmk_btc（10-10 19:22）「<span class="hl-key">抽奖送的硬件钱包，需要插入式的设备，一律不要使用</span>……今年很早期我在线下就知道有人要投硬件钱包投毒了，并且都是千万级别起投……所以一直以来私信我合作说抽奖送硬件钱包的活动我一个都没接」；② @0xJustdu（10-11 10:05）从叙事角度补刀：「<span class="hl">硬件钱包这个叙事随着这几年合规的发展被证伪了</span>。回想一下在这次 Ledger 出事前你多久没听说过硬件钱包了……以前区块链行业乱象丛生，基本上被盗之后没有任何机会找回，毕竟链上无实名」。</p>
    <p class="body-text"><b>要点</b>：① 上期（10-10）已收录「Ledger 经销商渠道被盗 8,700 万美元」，<b>本期新增的是攻击实现的实物证据</b> ——「屏幕显示什么就抓什么」意味着<span class="hl-key">此前被反复强调的「初始化时核对设备屏幕助记词」这条防御建议，恰恰是被攻破的那一环</span>，不要再把它当作可靠校验；② 设备外观、包装、防拆封条<b>可以完全正常</b>，唯一可靠的判别是<span class="hl-key">只从官方渠道直购 + 核对固件校验和 + 用第二台设备交叉校验助记词</span>；③ <b>@mmk_btc 的「插入式」说法是本期最可操作的一条经验规则</b> ——<span class="hl-key">任何来源不明、需要额外插入硬件（而非官方原装）的设备，一律不要初始化</span>；④ 引用链外部源 @MagicalTux 的帖子互动量（<span class="hl">103 万阅读</span>）远超白名单任何一条，<b>说明这个细节在英文圈是本期最大的传播点</b>，值得作为安全科普素材留档；⑤ 提醒：<b><span class="hl">这是经销商 / 供应链环节被动手脚，不是 Ledger 固件漏洞</span></b>，责任方与最终金额以官方调查结论为准。
    <span class="lnk">x.com/MagicalTux/status/2108583893809201216 · x.com/guanyuhan426/status/2108597428467433483 · x.com/mmk_btc/status/2108880898393571660 · x.com/0xJustdu/status/2109102946365411741 · protos.com/ledger-says-southeast-asia-reseller-linked-to-86m-draining/ · theblock.co/news/business/2026-10-09-ledger-cryptobilis-fund-losses-418163</span></p>
  </div>

  <div class="item">
    <div class="meta"><span class="src">X · @chairbtc</span>（白名单一手源）· 10-11 11:06 / 11:14 / 11:22 北京时间 <span class="tag warn">白名单一手源 · 周年复盘 + CZ 官方回应</span></div>
    <p class="body-text">@chairbtc 在 10-11 当天连发三条纪念<b>去年 10-11 大暴跌</b>：</p>
    <p class="body-text">① <b>数据口径</b>（11:14）：「纪念去年的 10.11 大暴跌，<span class="hl-key">160 多万人爆仓无家可归，全网爆仓金额超 400 亿美元</span>」；② <b>CZ 官方回应</b>（11:06）：「关于去年 10.11 大暴跌，很多人说是币安砸的盘，<b>CZ 对此回复：相关指责过于「牵强」，<span class="hl">币安称比特币触底后才开始脱锚</span></b>」；③ <b>三条操作纪律</b>（11:22）：「1、合约要养成止损或对冲的习惯；2、资产配置很重要，<span class="hl-key">80% 用来囤大饼，以太等会更抗跌，不要全部用来冲山寨或合约</span>；3、投资用闲钱去玩，不要借贷，或将大部分收入用作投资，一旦出现黑天鹅，会影响家庭运转以及夫妻感情」。</p>
    <p class="body-text"><b>要点</b>：① 这是<b>本期唯一由白名单账号给出的、带明确数字的周年复盘</b>（160 万人 / 400 亿美元），且 CZ 口径「币安在比特币触底后才开始脱锚」是<b>平台方对史上最大规模清算事件的正式定性</b>，与此前市场广泛流传的「币安砸盘」说法正面冲突 —— 引用时须标注为平台方立场，非独立调查结论；② 与上期报告「今日临时关注」中提到的「10/10 大清算一周年」是同一事件，<b>@chairbtc 用的是北京时间日期（10-11），英文媒体多用美东日期（10/10）</b>，做时间线对齐时注意差一天；③ 第三条的「<b>80% 囤大饼</b>」是本条最有操作性的部分 —— 在 ETF 连续流出、山寨分化加剧的当下（见 L1-4），这是白名单操盘手中偏保守的一档配置建议；④ 属白名单操盘手个人观点，<b>不构成投资建议</b>。
    <span class="lnk">x.com/chairbtc/status/2109118468268450241 · x.com/chairbtc/status/2109120479550423113 · x.com/chairbtc/status/2109122403439874433</span></p>
  </div>

  <div class="item">
    <div class="meta"><span class="src">Decrypt</span> + <span class="src">The Block</span> · 10-11 01:01 / 10-11 02:35 北京时间 <span class="tag new">监管边界划定</span></div>
    <p class="body-text"><b>CFTC 用新规给「预测市场 vs 赌博」划出明确边界，同期 Kalshi 正在自查一起内幕押注。</b></p>
    <p class="body-text">Decrypt：CFTC 提出的一项<b>正式规则</b>将把与体育、政治、文化、天气挂钩的事件合约<span class="hl-key">明确纳入「swap（掉期）」定义</span>，而一项<b>临时规则</b>把「赌场式赌博」排除在外 —— 这一步实质上强化了该机构对事件合约的<b>排他管辖权</b>。The Block（10-11 02:35）：<b><span class="hl">Kalshi 正在调查在 Trump 新闻秘书人选正式公布前就下注的账户</span></b>（疑似内幕交易）。</p>
    <p class="body-text"><b>要点</b>：① 这两条是同一件事的两面 —— <b>监管方在给赛道发「准生证」的同时，平台方在自查赛道最容易出事的环节（内幕交易）</b>；② 对预测市场赛道（Polymarket / Kalshi / Blockchain.com 新申请）的含义：<b><span class="hl-key">「是不是赌博」的定性风险正在下降，「内幕交易合规」的运营风险正在上升</span></b> —— 前者靠牌照解决，后者靠监控与 KYC，<b>做这类产品的团队现在必须把「谁在下注、下注时点是否异常」当成一级风控项</b>；③ 与上期 L3-3 的「Blockchain.com 申请 CFTC 牌照」连读，这条赛道本期是<b>监管与平台同步收敛</b>；④ 提醒：CFTC 的规则是<b>提案 + 临时规则</b>，未最终生效；Kalshi 的调查<b>尚未公布结论</b>，被调查不等于违规。
    <span class="lnk">decrypt.co/380635/cftc-draws-line-prediction-markets-and-gambling-new-rules · theblock.co/news/regulation/2026-10-10-kalshi-is-investigating-bets-on-trumps-press-secretary-pick-placed-be</span></p>
  </div>

  <div class="item">
    <div class="meta"><span class="src">The Block</span> · 10-10 23:10 北京时间 <span class="tag warn">资金面 · 分化信号</span></div>
    <p class="body-text"><b>美国以太坊现货 ETF 的<span class="hl-key">连续流出天数扩大到 9 天</span>，与此同时 <span class="hl-key">Solana 基金创下 14 周以来最强的单周流入</span>。</b></p>
    <p class="body-text"><b>要点</b>：① 这是本期<b>最清晰的资金轮动信号</b> —— 上期报告的「ETF 十月流出逼近 10 亿美元」在本期<b>没有反转，而是延续并分化</b>：ETH 端连续 9 日净流出，SOL 端却创 14 周最强流入；② 对做仓位的人：<b>「ETF 资金」这个口径已经不能再当成整个加密市场的同向指标</b>，ETH 与 SOL 的资金面正在背向而行，按「大盘 ETF 流入 = 全面看多」的逻辑交易会踩错；③ 与 L1-2 的 @chairbtc「80% 囤大饼」并读，<b>本期多个来源都在指向「不要把仓位押在单一山寨叙事上」</b>；④ 需注意：单周 ETF 流量噪声大，<b>14 周流入纪录是相对值（比过去 14 周强），不等于绝对规模巨大</b>。
    <span class="lnk">theblock.co/news/markets/2026-10-10-ether-etfs-extend-outflow-streak-to-nine-days-as-solana-funds-snap-recor</span></p>
  </div>

  <div class="item">
    <div class="meta"><span class="src">Cointelegraph</span> · 10-10 19:52 北京时间 <span class="tag new">抗量子叙事延续</span></div>
    <p class="body-text"><b><span class="hl-key">Justin Sun 称 Tron 的后量子密码学已在测试网上线。</span></b></p>
    <p class="body-text"><b>要点</b>：① 这是<b>本期「抗量子」这条线的第三个落点</b> —— 上期是 Starknet 宣布要做「首个完全抗量子 L1」（代币 +20%）与 V 神 / Justin Drake 的 bunker mode 之争，本期 Tron 直接<b>把后量子密码学部署到测试网</b>，从「路线图承诺」推进到「可验证代码」；② 对做技术评估的人：<b>「测试网」是关键限定词</b> —— 测试网部署不等于主网迁移，更不等于现有地址体系可平滑升级，Tron 的既有账户 / 合约 / 签名体系如何兼容后量子算法，文中未给细节；③ 与 L1-6 并读：<b>本期「抗量子」同时以叙事（Starknet）与工程（Tron）两种形态出现，但两者都还停在早期</b>，把它当交易理由的风险很高；④ 提醒：<b>Justin Sun 的公开声明一贯偏宣传口径</b>，测试网细节应以 Tron 官方仓库 / 区块浏览器为准，不要仅凭推文判断进度。
    <span class="lnk">cointelegraph.com/news/justin-sun-says-trons-post-quantum-cryptography-has-gone-live-on-testnet</span></p>
  </div>

  <div class="item">
    <div class="meta"><span class="src">Decrypt</span> + <span class="src">Cointelegraph</span> · 10-11 21:01 / 10-09 18:16 北京时间 <span class="tag new">税制 · 欧洲</span></div>
    <p class="body-text"><b>法国议会委员会支持对稳定币互换征税、并支持对加密资产离境征税，随后否决了整个预算案。</b></p>
    <p class="body-text">Decrypt：相关条款进入的是 <b>2027 年预算案</b>，委员会投票支持「<span class="hl-key">稳定币互换（stablecoin swap）课税</span>」与「<span class="hl-key">加密资产退出税（crypto exit tax）</span>」，但<b>整个预算案随后被否决</b>，这些条款的去留因此悬空。Cointelegraph（10-09 18:16）确认法国议员在 2027 预算法案中支持稳定币互换税。</p>
    <p class="body-text"><b>要点</b>：① <b>「稳定币互换」被单独立税是本期最值得记的方向性信号</b> —— 传统税法对「币币互换」长期处于灰色地带，法国这一步是要<b><span class="hl">把 USDC→USDT 这类「同价值互换」也纳入应税事件</span></b>，一旦在主要司法辖区落地，对做市、支付与稳定币套利的成本结构影响是结构性的；② 「加密退出税」针对的是<b>资产离境</b>（把资产转到境外 / 自托管），是资本管制思路在加密领域的延伸，与法国同期「7 个月 90 起针对持币者的暴力案件」（上期 L3-4）构成同一套政策组合 —— <b>税制透明 + 高调申报 = 定向目标暴露</b>；③ 提醒：<b>预算案已被否决，这些条款目前不是生效法律</b>，不要当成既成事实；④ 与上期「英国制裁 Cryptomus/TokenSpot」并读，<b>欧洲本期在「税」与「制裁」两条线上同时收紧</b>。
    <span class="lnk">decrypt.co/380630/france-stablecoin-swap-crypto-exit-tax · cointelegraph.com/news/french-lawmakers-back-stablecoin-swap-tax-in-2027-budget-bill</span></p>
  </div>
</section>

<section class="l2">
  <h2>L2 AI 工具与 Agent</h2>
  <p class="sub">只收工具实操与落地案例；AI 方向的重大新闻由「每日 AI 新闻推送」负责，本层不重复</p>

  <div class="item">
    <div class="meta"><span class="src">X · @Joensmoon</span>（白名单一手源）· 10-10 19:51 北京时间 <span class="tag new">Agent 落地 · 链上</span></div>
    <p class="body-text">@Joensmoon 给出 <b>Robinhood Chain</b> 的下一步方向判断：「目前关于接下来比较清晰的方向，是<span class="hl-key">把币股（Tokenized Stocks）和 AI Agent 真正结合起来</span>。官方最新的动向一直在推 <b>AI-native 的链定位</b>，加上 Agentic……」</p>
    <p class="body-text"><b>要点</b>：① 这是本期白名单里<b>唯一一条明确的「Agent 落地」线索</b>，且方向具体：不是泛泛谈 AI，而是<b>把「链上股票」这类有真实标的、有结算需求的资产，交给 Agent 去执行</b>；② 对做 Agent 产品的人，这个组合的可行性强于纯叙事 —— <b>代币化股票提供了 Agent 可操作的真实资产，链提供了可验证结算</b>，缺的是「Agent 的操作权限边界与追责机制」（参考上期 L2-1 汇丰 / 蚂蚁数科用代币化存款做 Agent 支付，银行侧补的正是风控与争议处理）；③ <b>安全侧必须同步考虑</b>：Agent 拿到资产处置权后，提示注入（prompt injection）的后果从「说错话」直接升级为「下错单」，与本层上期记录的微软 MXC 沙箱问题是同一类；④ 提醒：这是<b>白名单账号对官方动向的转述</b>，Robinhood Chain 的具体产品形态与时间表以官方公告为准。
    <span class="lnk">x.com/Joensmoon/status/2108888128912277630</span></p>
  </div>
</section>

<section class="l3">
  <h2>L3 链上机会</h2>
  <p class="sub">空投 · 打新 · 链上 Alpha · 具体标的与合约地址 · 风险预警</p>

  <div class="item">
    <div class="meta"><span class="src">X · @mmk_btc</span>（白名单一手源）· 10-10 21:30 北京时间 <span class="tag warn">具体标的 · 做空方向</span></div>
    <p class="body-text">@mmk_btc 给出<b>本期的做空标的选择</b>：「看到社区有人想空 <code>$spcx</code>，想了想还是说一下。<span class="hl-key">在 <code>$mrna</code> 没有新增业绩支持下，已经涨了 50%，这才是我优选的空标。</span>」</p>
    <p class="body-text"><b>要点</b>：① 这是<b>本期白名单唯一一条明确带方向（做空）与两个具体标的（$spcx / $mrna）的操盘判断</b>，信息密度高；② 他的逻辑不是「看跌大盘」，而是<b>「标的缺乏新增业绩支撑却已涨 50%」的相对价值判断</b> —— 属于「做空涨幅脱离基本面的个股」而非「做空市场」，风险特征与方向性做空不同；③ 提醒：<b>只给了标的与方向，没给入场位、止损位与仓位</b>，直接照抄的滑点与爆仓风险自担；且做空在流动性偏弱期（本期 ETF 分化、山寨普遍回撤）<b>容易被逼空</b>；④ 属白名单操盘手个人观点，<b>不构成投资建议</b>。
    <span class="lnk">x.com/mmk_btc/status/2108912977479110877</span></p>
  </div>

  <div class="item">
    <div class="meta"><span class="src">X · @Joensmoon</span>（白名单一手源）· 10-10 19:56 北京时间 <span class="tag hot">风险预警 · 喊单抢跑</span></div>
    <p class="body-text">@Joensmoon 对 <code>$PROM</code> 发出<b>喊单抢跑预警</b>：「敢情 <code>$PROM</code> 你们是喊单是吧，<b>我先跑了</b>。就算拉盘了这种车也是抢跑，反正我看我经常接喊单的朋友喊这个了，话说到这里了，<span class="hl-key">本来我都买了，梦回 <code>$ACE</code></span>。」</p>
    <p class="body-text"><b>要点</b>：① 这是<b>本期最有实操价值的一条风险预警</b>：他本人在车上，观察到「接喊单的朋友开始推」后主动离场，<b>「本来我都买了」说明这是基于持仓的实盘判断，不是旁观评论</b>；② 「<b>梦回 $ACE</b>」是关键参照 —— 指历史上同类型的「喊单 → 拉盘 → 接盘」模式，提醒的是<b>「拉盘」与「可持续」是两件事，抢跑的仓位即使吃到涨幅，退出通道也会被堵</b>；③ 可复用的观察方法：<b>把「喊单账号开始集中推某个标的」本身当成一个反向信号</b>，而不是当成利好；④ 提醒：<b>「喊单」是主观判断，未给出证据链</b>（谁在喊、喊单账号的持仓关联），不要据此认定 $PROM 项目方作恶；⑤ 属白名单操盘手个人观点，<b>不构成投资建议</b>。
    <span class="lnk">x.com/Joensmoon/status/2108889450147377494</span></p>
  </div>

  <div class="item">
    <div class="meta"><span class="src">X · @Joensmoon</span>（白名单一手源）+ <span class="src">X 外部一手源 @predictdotfun</span>（平台官方）· 10-10 18:39 / 10-09 22:02 北京时间 <span class="tag new">平台活动 · 积分机会</span></div>
    <p class="body-text"><b>Predict 官方宣布 25 万美元奖池投向 LOL 世界赛，@Joensmoon 给出完整赛事排期与赔率分布。</b></p>
    <p class="body-text">官方（@predictdotfun，10-09 22:02）：「Predict the Worlds. <b>$250k in prizes. Next week.</b>」@Joensmoon（10-10 18:39）补充细节：「Predict 又撒钱了！这次 <b>25 万刀砸 LOL 世界赛</b>，下周开打。<span class="hl-key">入围赛 10 月 15 号开始，总决赛 11 月 15 号，整整一个月的赛事周期</span>。目前盘面上 <b>LCK 70% LPL 24%</b>，冠军盘 <b>Gen.G 35%，HLE 和 BLG 各 20%，T1 17%</b>。」</p>
    <p class="body-text"><b>要点</b>：① <b>官方口径 + 白名单细节互相印证</b>，是本条质量较高的原因 —— 奖池金额与时间窗口均来自平台官方推文，非转述；② 可操作性在于<b>「整整一个月的赛事周期」</b>：与单场赛事相比，长周期赛事的赔率会随比赛进程反复波动，<b>给积分 / 流动性激励留出了多次参与的窗口</b>，而不是一次性抢跑；③ 赔率分布（LCK 70% / LPL 24%）本身也是市场情绪读数，<b>可用来观察中文区资金对 LPL 的实际押注比例</b>；④ 提醒：<b>这是平台自己的营销活动，奖池规则、结算口径与积分换算以 Predict 官方文档为准</b>，本日报仅转述公开信息。
    <span class="lnk">x.com/Joensmoon/status/2108869972302922183 · x.com/predictdotfun/status/2108558646745632983</span></p>
  </div>

  <div class="item">
    <div class="meta"><span class="src">X · @xtony1314</span>（白名单一手源）· 10-11 10:01 北京时间 <span class="tag new">账号动作 · 值得关注</span></div>
    <p class="body-text">@xtony1314 宣布<b>拆出独立交易账号</b>：「这个账号是本人个人账号，肯定不止是说交易，交易并不是我人生的全部……<span class="hl-key">所以我特地注册了一个账号 XiaoYao Capital，@XiaoYao_Capital 逍遥资本</span>。」</p>
    <p class="body-text"><b>要点</b>：① 这是<b>白名单成员的账号结构变更</b>，对做跟踪的人有直接意义 —— <b>此后他的交易内容大概率迁移到 @XiaoYao_Capital</b>，继续只盯老号会漏掉核心信号，<b>建议把新号加入监控清单</b>；② 「把交易与个人表达拆开」本身是一个信号：<b>当操盘手开始把交易内容产品化、机构化（用「Capital」命名）时，通常意味着从个人交易转向对外募集 / 品牌化运作</b>，后续可能出现产品、社群或资金管理动作，值得留意；③ 提醒：<b>新账号目前只有一条注册声明，无任何交易内容与业绩披露</b>，任何以「逍遥资本」名义的募资都应先核实与该账号的关联，<b>谨防同名冒充</b>；④ 属白名单账号的公开声明，本日报仅记录。
    <span class="lnk">x.com/xtony1314/status/2109101931289588214</span></p>
  </div>

  <div class="item">
    <div class="meta"><span class="src">The Block</span> · 10-09 21:12 北京时间 <span class="tag new">平台级方向</span></div>
    <p class="body-text"><b>Base 创始人 Jesse Pollak 表示：<span class="hl-key">股票代币化与非美元稳定币</span>将引领即将到来的「代币化超级周期」。</b></p>
    <p class="body-text"><b>要点</b>：① <b>Base（Coinbase 的 L2）创始人的方向表态，权重高于一般项目方</b> —— 他给出的两个抓手很具体：「<b>equities（股票代币化）</b>」与「<b>non-dollar stablecoins（非美元稳定币）</b>」，后者尤其值得注意，因为它指向的是<b>绕过美元稳定币单一格局</b>的路径；② 与 L2-1 的 Robinhood Chain「币股 + Agent」并读，<b>本期有两个独立来源都在押注「代币化股票」是下一阶段的主线</b>，这不是孤立观点；③ 与上期「Securitize 代币化美股上 Solana」连读，<b>「币股」赛道的竞争者已从单一项目扩展到 Base / Solana / Robinhood 三条链</b>，做这个方向的人应把「哪条链拿到发行方与合规通道」作为跟踪重点，而不是看链的 TPS；④ 提醒：<b>这是方向表态，不是产品发布</b>，无时间表与具体标的。
    <span class="lnk">theblock.co/news/defi/2026-10-09-tokenization-supercycle-base-jesse-pollak-418144</span></p>
  </div>

  <div class="item">
    <div class="meta"><span class="src">The Block</span> + <span class="src">Protos</span> · 10-09 18:40 / 10-09 21:40 北京时间 <span class="tag warn">亚洲 · 合规与风险</span></div>
    <p class="body-text"><b>① 泰国 SEC 的 BTC / ETH ETF 规则确定 <span class="hl-key">10 月 16 日生效</span></b>（The Block）—— 上期报告已收录「泰国敲定加密 ETF 规则」，<b>本期新增的是明确生效日 10-16</b>，且限定在泰国证券交易所（SET）交易。<b>② 中国发布三集杀猪盘（pig butchering）纪录片</b>（Protos，10-09 21:40）—— 官方媒体层面系统披露该类诈骗手法。</p>
    <p class="body-text"><b>要点</b>：① 泰国 ETF 的<b>生效日 10-16 落在本期节点模块的 7 天窗口内</b>，是可执行的观察点：<b>关注首批上市标的与成交额，这是判断「东南亚本地资金是否真的留在本地」的第一个实证</b>；② 中国官方发布杀猪盘纪录片，<b>对中文用户是直接的防诈信号</b> —— 这类内容通常在集中整治前发布，<b>后续可能出现针对相关引流渠道（社群、直播、婚恋平台）的更严处置</b>，做社群运营与投放的应提前评估合规边界；③ 两条并读的结论：<b>亚洲本期是「合规通道打开（泰国）」与「诈骗打击收紧（中国）」同时发生</b>，与上期「美国走 CFTC 牌照 / 法庭争定性」形成对照 —— <b>不同辖区在同时收紧与放开，跨境业务的政策风险差异在放大</b>；④ 提醒：泰国 ETF 的具体可交易标的与上线时间以 SET 公告为准；纪录片内容为官方宣传口径，<b>个案细节未经独立核实</b>。
    <span class="lnk">theblock.co/news/regulation/2026-10-09-thailand-sec-issues-bitcoin-and-ether-etf-rules-set-to-take-effect-oc · protos.com/china-releases-three-part-documentary-on-pig-butchering/</span></p>
  </div>
</section>

<section class="l4">
  <h2>L4 安全漏洞</h2>
  <p class="sub">CISA KEV 新增 · GitHub Advisory · HN 值得看的讨论（本节明细单独计数，不计入上方「最终收录」）</p>

  <h3>CISA KEV 已知被利用漏洞目录（本期无新增，最近入册 14 条）</h3>
  <p class="body-text">目录版本 <b>2026.10.08</b> · 共 <b>1739</b> 条，<b>与上期完全一致 —— 本期（10-10 — 10-11）无新增条目</b>。下表为最近入册批次（10-08 的 5 条为最新一批，上期已列），仅作索引保留。</p>
  <table>
    <tr><th>日期</th><th>CVE</th><th>厂商 / 产品</th><th>漏洞类型</th></tr>
    <tr><td class="date">10-08</td><td class="cve">CVE-2015-5477</td><td>ISC BIND</td><td>数据处理错误（TKEY 查询触发 DoS）</td></tr>
    <tr><td class="date">10-08</td><td class="cve">CVE-2016-3081</td><td>Apache Struts</td><td>命令注入（S2-032）</td></tr>
    <tr><td class="date">10-08</td><td class="cve">CVE-2023-22894</td><td>Strapi</td><td>敏感信息明文存储</td></tr>
    <tr><td class="date">10-08</td><td class="cve">CVE-2021-3199</td><td>ONLYOFFICE Docs</td><td>服务端路径穿越</td></tr>
    <tr><td class="date">10-08</td><td class="cve">CVE-2015-3306</td><td>ProFTPD</td><td>访问控制不当（mod_copy 任意文件复制）</td></tr>
    <tr><td class="date">10-04</td><td class="cve">CVE-2026-88779</td><td>Citrix NetScaler</td><td>内存缓冲区边界内操作限制不当</td></tr>
    <tr><td class="date">10-02</td><td class="cve">CVE-2026-102490</td><td>Zammad GmbH Zammad</td><td>权限管理不当</td></tr>
    <tr><td class="date">10-02</td><td class="cve">CVE-2026-102489</td><td>Zammad GmbH Zammad</td><td>会话固定（Session Fixation）</td></tr>
    <tr><td class="date">10-01</td><td class="cve">CVE-2026-104286</td><td>Fortinet FortiMail</td><td>路径穿越</td></tr>
    <tr><td class="date">09-30</td><td class="cve">CVE-2026-76504</td><td>Cisco Catalyst SD-WAN Manager</td><td>十六进制编码处理缺陷</td></tr>
    <tr><td class="date">09-29</td><td class="cve">CVE-2026-86950</td><td>Apple Multiple Products</td><td>越界写（CoreGraphics）</td></tr>
    <tr><td class="date">09-27</td><td class="cve">CVE-2026-88772</td><td>Citrix NetScaler</td><td>内存缓冲区边界内操作限制不当</td></tr>
    <tr><td class="date">09-27</td><td class="cve">CVE-2026-88771</td><td>Citrix NetScaler</td><td>输入校验不当</td></tr>
    <tr><td class="date">09-25</td><td class="cve">CVE-2026-67279</td><td>MikroTik RouterOS</td><td>行为工作流执行不当</td></tr>
  </table>
  <p class="body-text">本期 KEV 无新增，但上期那批「老 CVE 新入册」的行动建议依然有效，不要因为没上新闻就放下。10-08 一次性入册的五条全部是 2015–2023 年的老漏洞：<b>ISC BIND CVE-2015-5477</b>（DNS 解析层 DoS）、<b>Apache Struts CVE-2016-3081 / S2-032</b>（命令注入）、<b>ProFTPD CVE-2015-3306 / mod_copy</b>（任意文件复制）、<b>Strapi CVE-2023-22894</b>、<b>ONLYOFFICE Docs CVE-2021-3199</b>。CISA 把它们收进 KEV 的含义只有一个：<b>补丁早就存在、但正在被实际利用</b> —— 说明大量遗留系统仍在裸奔。若上期还没来得及处理，<b>BIND、Struts、ProFTPD 这三个应在本周内完成升级</b>；<b>Citrix NetScaler 一个月内已三次入册</b>，未打补丁的对外网关按「已被扫描」对待。</p>

  <h3>GitHub Security Advisory（最近发布，共 14 条）</h3>
  <p class="body-text">全部发布于 <b>2026-10-09</b>，<b>与上期同一批 —— 本期（10-10 — 10-11）GitHub 未发布新公告</b>（周末窗口）。本期最大簇是 <b>Vikunja 一次 7 条</b>，另有 <b>TinaCMS 3 条</b>（含 1 条 critical）、<b>Nginx-UI 2 条</b>（含 1 条 high）、<b>Shiny for Python 1 条</b>。下表保留作索引。</p>
  <table>
    <tr><th>严重度</th><th>CVE</th><th>包</th><th>问题</th></tr>
    <tr><td><span class="sev s-critical">critical</span></td><td class="cve">CVE-2026-108261</td><td class="pkg">tinacms</td><td>管理端预览 iframe 从 URL 片段加载攻击者可控的 origin</td></tr>
    <tr><td><span class="sev s-high">high</span></td><td class="cve">CVE-2026-107805</td><td class="pkg">github.com/0xJacky/Nginx-UI</td><td>未认证的签名请求体暂存可耗尽临时存储</td></tr>
    <tr><td><span class="sev s-high">high</span></td><td class="cve">CVE-2026-108259</td><td class="pkg">@tinacms/cli</td><td>生成的客户端源码中未转义的 Git 分支名导致代码注入</td></tr>
    <tr><td><span class="sev s-high">high</span></td><td class="cve">CVE-2026-108260</td><td class="pkg">@tinacms/web-components</td><td><code>tina-markdown</code> 把富文本链接 URL 直接写入 <code>href</code></td></tr>
    <tr><td><span class="sev s-high">high</span></td><td class="cve">—</td><td class="pkg">code.vikunja.io/api</td><td>宽松的跨域策略信任任意 localhost origin</td></tr>
    <tr><td><span class="sev s-medium">medium</span></td><td class="cve">CVE-2026-107804</td><td class="pkg">github.com/0xJacky/Nginx-UI</td><td>内置反向代理可绕过 IP 白名单并实现共享登录</td></tr>
    <tr><td><span class="sev s-medium">medium</span></td><td class="cve">CVE-2026-108258</td><td class="pkg">shiny</td><td>Shiny for Python 书签恢复存在路径穿越</td></tr>
    <tr><td><span class="sev s-medium">medium</span></td><td class="cve">—</td><td class="pkg">code.vikunja.io/api</td><td>写权限成员可通过链接分享删除管理员级分享</td></tr>
    <tr><td><span class="sev s-medium">medium</span></td><td class="cve">—</td><td class="pkg">code.vikunja.io/api</td><td>子项目上显式的低权限分享被静默覆盖</td></tr>
    <tr><td><span class="sev s-medium">medium</span></td><td class="cve">—</td><td class="pkg">code.vikunja.io/api</td><td>Webhook 与链接分享可逃过所有吊销路径</td></tr>
    <tr><td><span class="sev s-medium">medium</span></td><td class="cve">—</td><td class="pkg">code.vikunja.io/api</td><td>空过滤串创建保存视图会重算任务位置</td></tr>
    <tr><td><span class="sev s-medium">medium</span></td><td class="cve">—</td><td class="pkg">code.vikunja.io/api</td><td>WebSocket 认证忽略服务端会话状态，已吊销会话仍可用</td></tr>
    <tr><td><span class="sev s-medium">medium</span></td><td class="cve">—</td><td class="pkg">code.vikunja.io/api</td><td>只读项目成员可通过接口获取指派者邮箱</td></tr>
    <tr><td><span class="sev s-low">low</span></td><td class="cve">—</td><td class="pkg">code.vikunja.io/api</td><td>任务关系删除未校验对另一端任务的读权限</td></tr>
  </table>
  <p class="body-text">本期三个簇各有明确的利用路径，值得逐一记。<b>① TinaCMS 3 条是「同一个 CMS 的攻击链三段」</b>：critical 那条是<b>管理端预览 iframe 从 URL 片段加载攻击者可控 origin</b>（配合 XSS 可直接打管理员会话），另两条分别是<b>构建期代码注入（未转义的 Git 分支名写进生成的客户端源码）</b>与<b>渲染期 href 注入</b> —— <b>「把不可信数据拼进可执行 / 可导航上下文」的三种变体</b>，与 L2-1 的 Agent 权限问题正好互为补充（沙箱管执行时隔离，这三条要的是生成与渲染时不拼接）。<b>② Nginx-UI 2 条是典型的「运维面板」风险</b>：<b>未认证即可用签名请求体撑爆临时存储</b>（DoS，无需登录）+ <b>内置反向代理可绕过 IP 白名单并共享登录</b>（把「只允许内网访问」的保护直接废掉）—— <b>Nginx-UI 常被暴露在公网做面板</b>，这两条合起来是「无需认证的入口 + 白名单失效」的组合，应优先升级。<b>③ Vikunja 的 7 条是一条完整的「授权模型失效」清单</b>：CORS 信任任意 localhost origin（high）+ 低权限删管理员分享 + 子项目权限被静默覆盖 + Webhook / 链接分享逃过所有吊销路径（撤销后仍有效）+ WebSocket 认证忽略服务端会话状态（吊销的会话仍可用）+ 只读成员可见指派者邮箱 —— <b>对做 Web 安全测试的人是现成的测试清单</b>：重点测「吊销是否真的生效」「子资源是否继承父级权限」「跨域策略是否只白名单了具体 origin 而不是整个 localhost」。<b>④ Shiny for Python 的书签恢复路径穿越</b>是数据应用侧的老问题，自建 Shiny 服务的需升级。</p>

  <h3>Hacker News 24 小时内 &gt;80 分热门（共 20 条，另剔除 1 条涉时政）</h3>
  <table>
    <tr><th>分数</th><th>标题</th></tr>
    <tr><td class="pts">427</td><td><a href="https://beaksec.github.io/posts/telegram-desktop-one-click-account-takeover/">Telegram Desktop vulnerability allowed any user's file to be stolen</a></td></tr>
    <tr><td class="pts">380</td><td><a href="https://cphpost.dk/2026-10-10/news/round-up/123456-password-used-in-massive-danish-cpr-data-breach/">`123456' password used in Danish CPR data breach</a></td></tr>
    <tr><td class="pts">358</td><td><a href="https://community.bitwarden.com/t/published-version-update-in-app-stores/102750">Bitwarden Dual License Model</a></td></tr>
    <tr><td class="pts">286</td><td><a href="https://lightbulbcomputer.com/">The Lightbulb Computer</a></td></tr>
    <tr><td class="pts">264</td><td><a href="https://www.opengroup.org/openbrand/register/">Apple/macOS removed from official Unix registry</a></td></tr>
    <tr><td class="pts">262</td><td><a href="https://github.com/rociiu/talorys">Talorys – A self-hosted personal AI agent on Cloudflare's free tier</a></td></tr>
    <tr><td class="pts">225</td><td><a href="https://conversableeconomist.com/2026/09/28/i-would-like-the-value-of-my-home-to-rise/">I would like the value of my home to rise, while my property taxes fall</a></td></tr>
    <tr><td class="pts">216</td><td><a href="https://housing.over.pizza/">A city-building game in which the city would prefer you didn't</a></td></tr>
    <tr><td class="pts">196</td><td><a href="https://wiki.cateat.fish/art:computers_cannot_make_decisions">Computers Cannot Make Decisions</a></td></tr>
    <tr><td class="pts">175</td><td><a href="https://www.theguardian.com/us-news/2026/oct/10/fda-toxic-chemicals-food-analysis">FDA may allow some toxic chemicals to be added to food without safety review</a></td></tr>
    <tr><td class="pts">162</td><td><a href="https://www.thomas-huehn.com/knuth-reward-check/">Knuth reward check</a></td></tr>
    <tr><td class="pts">160</td><td><a href="https://motherduck.com/blog/why-duckdb-20-is-faster/">Why DuckDB 2.0 is faster</a></td></tr>
    <tr><td class="pts">157</td><td><a href="https://nishtahir.com/build-your-own-decision-model/">Build your own decision model</a></td></tr>
    <tr><td class="pts">140</td><td><a href="https://wallhop.io/">WallHop – 12ft.io is gone, so I built a replacement</a></td></tr>
    <tr><td class="pts">131</td><td><a href="https://www.ft.com/content/052610c5-22b4-4dd4-932e-b7f9f0628b6a">Nvidia in talks to acquire US 'open' model startup Reflection AI</a></td></tr>
    <tr><td class="pts">121</td><td><a href="https://chronicles.popvax.com/p/popvax-goes-clinical">PVX-001: open-source Covid-19 vaccine starts Phase 1 trial</a></td></tr>
    <tr><td class="pts">117</td><td><a href="https://news.vt.edu/articles/2026/10/research_fralinbiomed_upfhutelin.html">Food processing influences metabolism and brain activity</a></td></tr>
    <tr><td class="pts">116</td><td><a href="https://ghuntley.com/unikernels/">Unikernels were hard. key word: were</a></td></tr>
    <tr><td class="pts">103</td><td><a href="https://en.wikipedia.org/wiki/Takeshi%27s_Castle">Takeshi's Castle</a></td></tr>
    <tr><td class="pts">90</td><td><a href="https://kotaku.com/we-might-be-cooked-as-these-vibe-coded-web-browser-ports-of-halo-the-simpsons-hit-and-run-and-gta-work-well/">Vibe coded browser ports of Halo, The Simpsons: Hit And Run, GTA work well</a></td></tr>
  </table>
  <p class="body-text">本期值得点的四条：<b>① Telegram Desktop 一键账号接管（427 分 / 274 评论，本期最高）</b> —— 利用 Telegram Desktop 的本地文件处理缺陷，<b>任意用户可窃取他人的任意文件</b>，属「桌面端信任边界」问题；对做安全的人是高价值阅读材料，对普通用户<b>应立即升级 Telegram Desktop</b>。<b>② 丹麦 CPR（国家人口登记）数据泄露用 <code>123456</code> 当口令（380 分 / 194 评论）</b> —— 国家级公民数据库的弱口令，是「合规 ≠ 安全」的极端案例，与本期 L4 的 KEV 老漏洞被实际利用是同一类根因：<b>基础卫生没做到，与漏洞库新旧无关</b>。<b>③ Bitwarden 双许可模式变更（358 分 / 258 评论）</b> —— 密码管理器调整许可条款，对自建 / 二次分发的团队有直接影响，值得点进原帖看社区的具体争议点。<b>④ WallHop：12ft.io 关停后的替代品（140 分）</b> —— 对做信息收集与内容检索的人是个实用工具，<b>但付费墙绕过的法律边界在各地不同，仅建议用于公开内容的可访问性问题</b>。另有 <b>Nvidia 洽谈收购 Reflection AI（131 分）</b>，属 AI 方向，归口「每日 AI 新闻推送」。</p>
</section>

<footer>
  <p>共收录 <b>13</b> 条（L1 6 · L2 1 · L3 6）；L4 表格另计 <b>48</b> 条明细（CISA KEV 14 · GitHub Advisory 14 · HN 20）。所有时间均为北京时间。</p>
  <p class="foot-log">剔除明细、数据源执行情况与主线复盘见配套日志：<code>DailyIntel\logs\2026-10-11-剔除与执行日志.md</code></p>
</footer>
"""

HTML = ("<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>情报收集 · 2026-10-11</title>\n<style>" + CSS + "</style>\n</head>\n<body>\n"
        "<div class=\"wrap\">\n" + BODY + "\n</div>\n</body>\n</html>\n")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with io.open(OUT, "w", encoding="utf-8") as f:
    f.write(HTML)
print("wrote", OUT, len(HTML), "chars")

# ---------------------------------------------------------------- 配套日志
LOG_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "logs", "2026-10-11-剔除与执行日志.md")
LOG_MD = r"""# 情报收集 · 2026-10-11 — 剔除与执行日志

> 本文件是《情报收集 · 2026-10-11》的配套日志，承接不进成品的**剔除明细、数据源执行情况、主线复盘**。
> 成品报告：`<Desktop>\情报收集\2026-10-11-情报收集.html`
> 覆盖窗口：北京时间 10-09 11:18 — 10-11 11:18（48 小时）

---

## 一、口径

- 共收录 **13** 条（L1 6 · L2 1 · L3 6）。
- L4 表格另计 **48** 条明细（CISA KEV 14 · GitHub Advisory 14 · HN 20，另剔除 1 条涉时政），**不计入上列总数**。
- 市场情绪总览模块的数据源与条数不计入正文收录数。

---

## 二、剔除规则（沿用，未改）

1. **绝不按简介 / 邀请码过滤。** 链上操盘手与打狗选手普遍挂邀请码变现，但内容是必看的实操来源，误杀损失最大。本期 X 通道 15/15 正常，白名单账号中的返佣 / 邀请码内容一律**按内容价值判断，不按简介过滤**。
2. **只剔除这一类**：推文既无具体标的（$XXX）、又无买卖动作（买入 / 加仓 / 减仓 / 清仓 / 止盈 / 止损 / 埋伏 / 挂单 / 打狗 / 打新）、又无 0x 链上地址，且只堆邀请码与交易所广告的纯拉人头内容。
3. **其余剔除**：抽奖钓鱼（转发 + 点赞 + 留地址）、纯情绪短句（GM / 早安 / 光秃秃钱包地址）、生活流水（吃饭 / 购物 / 收藏 / 节日祝福）、交易所区域翻译号（「由 Grok 翻译」这类）、无简介僵尸号、**涉及时政的内容**。
4. **窗口重叠**：48 小时窗口与上一期重叠约 21 小时，**上一期已收录的条目本期不重复推送**，单列见第四节。

---

## 三、本期剔除明细（24 条）

### ① 情绪短句 / 段子 / 生活流水 —— 12 条

| 账号 | 内容摘要 | 备注 |
|---|---|---|
| @chairbtc | 「老马最近又在清理僵尸粉了……掉粉就和掉发一样容易」 | — |
| @0xJustdu | 「还是不能跟技师太熟……」 | 596 赞 |
| @0xJustdu | 「大多数男性还是高估了自己的魅力」 | — |
| @0xJustdu | 「果然痛苦就是创作的源泉」 | 段子 |
| @xtony1314 | 「这多少带点脑瘫了，孙哥的眼神像看到一只猴」 | 481 赞，八卦 |
| @xtony1314 | 「托尼老师纹了一个过江龙」 | — |
| @xtony1314 | 「昨晚吃了安眠药莱博雷生……梦中梦」 | — |
| @BTCdayu | 「双汇也是大牌子、老牌子」 | — |
| @BTCdayu | 「刹车不是不踩，而是缓踩、慢踩、优踩」 | 段子 |
| @aa_AFeng | 「通过自己努力得到收获……行情好的时候我基本一天枯坐 18 小时」 | 125 赞，交易心得，无标的无动作 |
| @mmk_btc | 「我突然明白了天道……人妖殊途」 | — |
| @Web3shenqing | 「十一过完了，工作室得上班了吧」 | — |
| @wolfyxbt | 「马斯克对我越来越抠搜了……现在只剩七百刀了」 | 231 赞，收入流水 |

> 互动量高但**无标的、无买卖动作**，按规则不进正文。

### ② 玩梗 / 泛论 —— 3 条

- @wolfyxbt「我再指一条赛道：中文世界的 @gattouz0」（217 赞）
- @AlanShao111「再指一条赛道：中文世界的 Joe Rogan」（397 赞，外部一手源）
- @BNBCHAIN「Ran into @jadoodoo_ at BNB Singapore」

### ③ 涉时政 —— 1 条

- @xtony1314「新加坡模式应该就是中国的终究梦想……新加坡本质就是个迷你版的中国」（308 赞）。**按规则剔除。**

### ④ 平台花絮 / 营销 —— 5 条

- @GoldenCicada「4M 在新加坡 2049 请男模」（上期同条已剔除）
- @GoldenCicada「F1 预热赛 现场还是很震撼的」（上期同条已剔除）
- @GoldenCicada「有幸在 @luxiong_Gate 的邀请下参加了 Gate 晚宴」
- @mmk_btc「Token2049 全程唯一遗憾是没跟西八姐合影」
- @4MBossChen「谁说币圈冷清了？你们想看的 4M 带你看」（外部引用链，上期同条已剔除）

### ⑤ 纯拉人头 / 返佣推广 —— 1 条

- @Joensmoon「现在新用户没那么多了……之前注册了没绑码的、这批人补绑一下手续费拿回去，DM:…」

> **注**：白名单中其余带邀请码 / 返佣的推文均**按内容价值保留**，未按简介过滤。

### ⑥ 未经证实的社区指控 —— 1 条

- @gnn1948944「我严重怀疑阿峰是一个机构……一天 24 小时，这逼能交易 25 小时」（51 赞，外部引用链）
- 属对个人未经证实的猜测，无标的无动作，不进正文。

### ⑦ AI 方向 —— 1 条

- 本期白名单无 AI 方向可剔条目；HN 中的 Nvidia 收购 Reflection AI 归口「每日 AI 新闻推送」。

---

## 四、上期已收录、本期不重复（1 条）

本期窗口（10-09 11:18 — 10-11 11:18）与上一期（10-10，窗口 10-08 08:30 — 10-10 08:30）**重叠约 21 小时**。

- @ytflzyyds「OKX 扔出了两个王炸……渣打、Circle、Ripple、QRT + ICE 战略投资，250 亿美元估值」（10-09 16:20，上期 L3-2）

> **注**：重叠段内另有 4 条（@GoldenCicada 的 4M 男模、F1 预热赛，@4MBossChen 的 4M 营销）在上期已被剔除，本期维持剔除，**未计入「上期已收录」**。

---

## 五、数据源与执行情况

### X 白名单（主通道）

- **15/15 全部成功**，本期为完整版。
- 直连探测 `curl -m 8 https://x.com/aa_AFeng` → **000**（不通），改走 Clash 轮换通道（经 `127.0.0.1:7897`，实测该出口访问 x.com 返回 200），**换节点 8 次**，结束已自动恢复「🇺🇸美国 04 | 专线」。
- 原始 **103** 条 → 48 小时窗口内 **38** 条，**低于**修复后常规区间（43–57）。
- 已逐项核查**非解析器回退**：切分锚点 `rest_id:"<id>",result:$R[n]={` 有效、ID / 时间 / 正文 / 互动数四项对齐、15 个账号全部返回 200。
- 偏低的真实原因：**窗口内零产出账号多达 4 个** —— @SuperL9（最新 10-08 17:45）、@maid_crypto（10-07 17:51）、@JieChao13754（03-22 停更）、@machibigbrother（10-09 01:20，刚好出界）；叠加周末效应。
- **引用链外部一手源**：@MagicalTux、@guanyuhan426、@AlanShao111、@gnn1948944、@predictdotfun、@4MBossChen、@BNBCHAIN。其中 **@MagicalTux 的 Ledger 硬件植入实物图（1,102 赞 / 103 万阅读）是本期 L1-1 的核心证据** —— 引用链抓取是净增益。

### 本期修复的两处环境变更

1. **Clash 订阅整体更换** —— 原「寿司云」策略组消失，Clash API `GET /proxies/寿司云` 返回 **404**（不是前两期的 400），脚本在 `group_now()` 阶段即 traceback。新机场为「**一元机场**」（Selector，20 节点）。已**逐节点实测**：18 个真实节点（港 01–04 / 日 01–10 / 美 01–04）访问 x.com **全部 200**，据此重建 `NODES` 白名单。
2. **SSR `views` 字段格式变更** —— 由 `views:{count:"N"}` 变为 `views:$R[n]={count:"N"}`，旧正则导致 12 条推文 views 全为 `None`。已修复为兼容两种形式。

### 外部源

| 源 | 状态 | 备注 |
|---|---|---|
| CISA KEV | 正常 | 版本 **2026.10.08 / 1739 条**，**本期无新增**（与上期一致） |
| GitHub Advisory | 正常 | **14 条，最新 10-09，与上期同一批** —— 周末无新发布 |
| Hacker News | 正常 | 21 条 >80 分，剔 1 条时政 = 20 |
| Decrypt / Cointelegraph | 正常 | 多数条目与上期重合，本期新增 CFTC 预测市场新规、Meanwhile 融资、法国稳定币税、Tron 后量子测试网 |
| The Block | **本期新增可用** | 20 条，时效最好；本期 L1-3 / L1-4 / L3-5 / L3-6 主源 |
| Protos | **本期新增可用** | 10 条；Ledger 细节 + 中国杀猪盘纪录片 |
| CoinGecko | 正常但限流 | 免费档 **429 严重**，调用间隔需 ≥4s |
| Binance 公告端点 | 仍 400 | — |
| rekt.news | 仍失败 | SSL 超时 |
| cryptoslate RSS | **本期 403** | 上期还可用 |
| blockworks RSS | 返回 0 条 | — |

### 市场情绪数据源

- **恐惧贪婪指数**：CoinMarketCap 官方接口（`pro-api.coinmarketcap.com`），**免密钥 Keyless 通道** `/public-api/v3/fear-and-greed/historical?count=30`。
- **大盘**：同一通道 `/v1/global-metrics/quotes/latest`。
- **爆仓**：OKX 公共接口（CoinGlass 无免费额度，最低 $29/月）。
- **合约情绪**：Binance 合约公共 API。

---

## 六、本期三条主线

### ① 「硬件钱包」这条安全防线被从物理层击穿

Ledger 供应链攻击的实物证据（屏幕与主板之间的植入模块 + 4G 外发）曝光（L1-1），白名单侧随即出现两条独立反应（@mmk_btc「插入式设备一律不用」、@0xJustdu「硬件钱包叙事被证伪」）。

**上期还在讨论「经销商渠道被盗」，本期已经能看见作案硬件的照片 —— 从「别初始化」升级为「别相信屏幕」。** 这是本期最值得记的结构性变化。

### ② 资金与叙事同时出现分化

ETH ETF 连续 9 日流出、Solana 基金创 14 周流入纪录（L1-4）；「抗量子」以叙事（Starknet，上期）与工程（Tron 测试网，L1-5）两种形态并行推进；@chairbtc 在周年复盘中给出的建议是「**80% 囤大饼**」（L1-2）。

**市场正在从「押单一叙事」转向「分档配置」。**

### ③ 监管在同时收紧与放开，且边界在细化

CFTC 给预测市场划「swap vs 赌博」的线并同步出现 Kalshi 内幕押注自查（L1-3）、法国对稳定币互换与资产离境单独立税（L1-6）、泰国 ETF 规则定档 10-16（L3-6）、中国发布杀猪盘纪录片（L3-6）。

**「能不能做」的政策风险在下降，「怎么做才合规」的运营风险在上升。**

行情侧对应的是**横盘偏强**（BTC $82,907 / +0.48%，NEAR +5.73% 领先，SOL / XRP / DOGE 小幅回落），但 ETF 端的结构性分化说明**指数级别的平静掩盖了内部的资金再分配**。

---

## 七、市场节点

- `events.json` / `calendar-extra.json` **未增删**，未重跑 `build_tasks.py` / `build_meeting_log.py` / `build_ics.py`。
- 本期抓取到的唯一新时间节点是 **泰国加密 ETF 规则 10-16 生效** —— 属区域性合规节点，非全球市场数据节点，仅记于 L3-6 正文。
- 未来 7 天节点模块由脚本按现有配置生成，见报告顶部。

---

## 八、本期数据快照（存档）

| 指标 | 值 |
|---|---|
| 恐惧贪婪指数 | **57 中性**（昨 56 / 7 天前 67 / 30 天前 68） |
| 全球总市值 | $2.80T（24h +0.18%） |
| 现货 24h 成交额 | $42.5B |
| 合约 24h 成交额 | $322.4B（现货的 7.6 倍） |
| BTC 占比 | 59.50% |
| OKX 24h 爆仓 | BTC 空爆 $653K vs 多爆 $103K；ETH 空爆 $2.07M vs 多爆 $555K |
| Binance BTC 资金费率 | -0.0011%（24h 均值） |
| ETH 散户 / 大户多空比 | 2.96 / 1.57 |
"""
os.makedirs(os.path.dirname(LOG_OUT), exist_ok=True)
with io.open(LOG_OUT, "w", encoding="utf-8") as f:
    f.write(LOG_MD)
print("wrote", LOG_OUT, len(LOG_MD), "chars")
