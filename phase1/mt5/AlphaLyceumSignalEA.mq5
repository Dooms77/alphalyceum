//+------------------------------------------------------------------+
//|                                              AlphaLyceumSignalEA |
//|             Phase 1: Signal + Visual + Backtest Execution Mode   |
//+------------------------------------------------------------------+
#property strict
#include <Trade/Trade.mqh>

input string InpSymbol            = "";              // kosong = pakai symbol chart
input ENUM_TIMEFRAMES InpTF       = PERIOD_M15;
input int InpEMAPeriod            = 50;
input int InpRSIPeriod            = 3;
input double InpRSILow            = 20.0;
input double InpRSIHigh           = 80.0;
input int InpADXPeriod            = 5;
input double InpADXMin            = 30.0;
input int InpSwingLookback        = 5;
input double InpRR                = 3.0;
input bool InpUseCommonFile       = true;
input string InpOutFile           = "alphalyceum_signals.jsonl";

// Debug / diagnostics
input bool InpDebugMode           = false; // prints condition states on each new bar
input bool InpTestEmitOnInit      = false; // emits one TEST signal on init (proves file writing)

// Logic tuning (M5-friendly)
input bool InpUseCrossOnly        = false; // if true, requires RSI cross; if false, allows RSI zone-touch OR cross
input bool InpRequireConfirmBreak = false; // if true, requires close break of signal candle high/low; if false, only needs candle direction

input bool InpShowIndicators      = true;
input bool InpShowStatusPanel     = true;

// V4 filters
input bool InpUseSessionFilter    = true;
input int InpSessionStartHour     = 12;   // server time
input int InpSessionEndHour       = 23;   // server time
input int InpATRPeriod            = 14;
input double InpMinATRPoints      = 150.0;
input double InpMaxSpreadPoints   = 120.0;

// Backtest execution only (biar tester ada trade metrics)
input bool InpEnableBacktestExecution = true;
input bool InpUseCompoundingRisk      = true;
input double InpRiskPercent           = 1.0;   // risk % dari equity per trade
input double InpBacktestLot           = 0.10;  // dipakai jika compounding off
input double InpMinLot                = 0.01;
input double InpMaxLot                = 2.00;
input bool InpOnePositionOnly         = true;
input string InpRunId                 = "";    // autolab run id for metrics export

int hEma = INVALID_HANDLE;
int hRsi = INVALID_HANDLE;
int hAdx = INVALID_HANDLE;
int hAtr = INVALID_HANDLE;
datetime lastBarTime = 0;
datetime lastSignalBar = 0;
string tradeSymbol = "";
string statusObjName = "ALPHALYCEUM_STATUS";
CTrade trade;

//+------------------------------------------------------------------+
int OnInit()
{
   tradeSymbol = (StringLen(InpSymbol) > 0 ? InpSymbol : _Symbol);
   if(_Symbol != tradeSymbol)
      Print("[AlphaLyceum] Info: chart=", _Symbol, " tradeSymbol=", tradeSymbol);

   hEma = iMA(tradeSymbol, InpTF, InpEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   hRsi = iRSI(tradeSymbol, InpTF, InpRSIPeriod, PRICE_CLOSE);
   hAdx = iADX(tradeSymbol, InpTF, InpADXPeriod);
   hAtr = iATR(tradeSymbol, InpTF, InpATRPeriod);

   if(hEma == INVALID_HANDLE || hRsi == INVALID_HANDLE || hAdx == INVALID_HANDLE || hAtr == INVALID_HANDLE)
   {
      Print("[AlphaLyceum] Failed to create indicator handles");
      return(INIT_FAILED);
   }

   if(InpShowIndicators)
      AttachVisualIndicators();

   if(InpShowStatusPanel)
      CreateStatusPanel();

   UpdateStatus("READY", clrAqua, 0.0, 0.0);
   Print("[AlphaLyceum] Initialized successfully");

   if(InpTestEmitOnInit)
   {
      string nowt = TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS);
      string id = "TEST-" + tradeSymbol + "-" + EnumToString(InpTF) + "-" + nowt;
      StringReplace(id, ":", "");
      StringReplace(id, ".", "");
      StringReplace(id, " ", "-");
      string json = StringFormat("{\"id\":\"%s\",\"pair\":\"%s\",\"tf\":\"%s\",\"side\":\"TEST\",\"entry\":0,\"sl\":0,\"tp\":0,\"rr\":\"0\",\"adx\":0,\"rsi\":0,\"signal_time\":\"%s\",\"source\":\"test_init\"}",
                               id, tradeSymbol, EnumToString(InpTF), nowt);
      Print("[AlphaLyceum] Emitting test signal on init");
      WriteSignal(json);
   }

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(hEma != INVALID_HANDLE) IndicatorRelease(hEma);
   if(hRsi != INVALID_HANDLE) IndicatorRelease(hRsi);
   if(hAdx != INVALID_HANDLE) IndicatorRelease(hAdx);
   if(hAtr != INVALID_HANDLE) IndicatorRelease(hAtr);

   if(MQLInfoInteger(MQL_TESTER) != 0)
      WriteBacktestMetrics();

   if(ObjectFind(0, statusObjName) >= 0)
      ObjectDelete(0, statusObjName);
}

//+------------------------------------------------------------------+
void OnTick()
{
   datetime barTime = iTime(tradeSymbol, InpTF, 0);
   if(barTime == 0)
      return;

   if(barTime != lastBarTime)
   {
      lastBarTime = barTime;
      EvaluateSignal();
   }
   else
   {
      double rsi0 = GetBufferValue(hRsi, 0, 0);
      double adx0 = GetBufferValue(hAdx, 0, 0);
      UpdateStatus("WAITING", clrSilver, rsi0, adx0);
   }
}

//+------------------------------------------------------------------+
void AttachVisualIndicators()
{
   long cid = ChartID();
   ChartIndicatorAdd(cid, 0, hEma);
   ChartIndicatorAdd(cid, 1, hRsi);
   ChartIndicatorAdd(cid, 2, hAdx);
}

//+------------------------------------------------------------------+
void CreateStatusPanel()
{
   if(ObjectFind(0, statusObjName) >= 0)
      ObjectDelete(0, statusObjName);

   ObjectCreate(0, statusObjName, OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, statusObjName, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, statusObjName, OBJPROP_XDISTANCE, 12);
   ObjectSetInteger(0, statusObjName, OBJPROP_YDISTANCE, 22);
   ObjectSetInteger(0, statusObjName, OBJPROP_FONTSIZE, 9);
   ObjectSetString(0, statusObjName, OBJPROP_FONT, "Consolas");
}

//+------------------------------------------------------------------+
void UpdateStatus(string mode, color c, double rsiVal, double adxVal)
{
   if(!InpShowStatusPanel || ObjectFind(0, statusObjName) < 0)
      return;

   string t = StringFormat(
      "ALPHALYCEUM BOT\nSym: %s  TF: %s\nMode: %s\nRSI(3): %.2f  ADX(5): %.2f\nRule: EMA50 + RSI20/80 cross + ADX>%.0f",
      tradeSymbol, EnumToString(InpTF), mode, rsiVal, adxVal, InpADXMin
   );

   ObjectSetString(0, statusObjName, OBJPROP_TEXT, t);
   ObjectSetInteger(0, statusObjName, OBJPROP_COLOR, c);
}

//+------------------------------------------------------------------+
void EvaluateSignal()
{
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(tradeSymbol, InpTF, 0, 30, rates) < 10)
      return;

   double ema[];
   double rsi[];
   double adx[];
   double atr[];
   ArraySetAsSeries(ema, true);
   ArraySetAsSeries(rsi, true);
   ArraySetAsSeries(adx, true);
   ArraySetAsSeries(atr, true);

   if(CopyBuffer(hEma, 0, 0, 30, ema) < 10) return;
   if(CopyBuffer(hRsi, 0, 0, 30, rsi) < 10) return;
   if(CopyBuffer(hAdx, 0, 0, 30, adx) < 10) return;
   if(CopyBuffer(hAtr, 0, 0, 30, atr) < 10) return;

   // signal candle = [2], confirmation candle = [1]
   bool trendBuy = rates[2].close > ema[2];
   bool trendSell = rates[2].close < ema[2];
   bool rsiBuyCross = (rsi[3] < InpRSILow && rsi[2] > InpRSILow);
   bool rsiSellCross = (rsi[3] > InpRSIHigh && rsi[2] < InpRSIHigh);

   // RSI trigger: allow zone-touch as well as cross (configurable)
   bool rsiBuyZone = (rsi[2] <= InpRSILow);
   bool rsiSellZone = (rsi[2] >= InpRSIHigh);

   bool rsiBuyOK = InpUseCrossOnly ? rsiBuyCross : (rsiBuyCross || rsiBuyZone);
   bool rsiSellOK = InpUseCrossOnly ? rsiSellCross : (rsiSellCross || rsiSellZone);

   bool adxStrong = adx[2] >= InpADXMin;

   bool bullCandle = (rates[1].close > rates[1].open);
   bool bearCandle = (rates[1].close < rates[1].open);

   bool confirmBull = InpRequireConfirmBreak ? (rates[1].close > rates[2].high && bullCandle) : bullCandle;
   bool confirmBear = InpRequireConfirmBreak ? (rates[1].close < rates[2].low && bearCandle) : bearCandle;

   if(InpDebugMode)
   {
      Print(StringFormat("[AlphaLyceum][DBG] %s %s TF=%s | trendBuy=%d trendSell=%d | rsi(3)=%.2f rsi(2)=%.2f crossBuy=%d crossSell=%d zoneBuy=%d zoneSell=%d rsiBuyOK=%d rsiSellOK=%d | adx(2)=%.2f strong=%d | confirmBull=%d confirmBear=%d",
                         tradeSymbol,
                         TimeToString(rates[1].time, TIME_DATE|TIME_MINUTES),
                         EnumToString(InpTF),
                         (int)trendBuy, (int)trendSell,
                         rsi[3], rsi[2],
                         (int)rsiBuyCross, (int)rsiSellCross,
                         (int)rsiBuyZone, (int)rsiSellZone,
                         (int)rsiBuyOK, (int)rsiSellOK,
                         adx[2], (int)adxStrong,
                         (int)confirmBull, (int)confirmBear));
   }

   // V4 filters
   double spreadPoints = (SymbolInfoDouble(tradeSymbol, SYMBOL_ASK) - SymbolInfoDouble(tradeSymbol, SYMBOL_BID)) / _Point;
   bool spreadOk = (spreadPoints <= InpMaxSpreadPoints);
   double atrPoints = atr[2] / _Point;
   bool atrOk = (atrPoints >= InpMinATRPoints);
   bool sessionOk = IsSessionAllowed(rates[1].time);

   datetime signalBar = rates[1].time;
   if(signalBar == lastSignalBar)
   {
      UpdateStatus("WAITING", clrSilver, rsi[1], adx[1]);
      return;
   }

   if(trendBuy && rsiBuyOK && adxStrong && confirmBull && spreadOk && atrOk && sessionOk)
   {
      EmitSignal("BUY", rates, rsi[2], adx[2]);
      DrawSignalArrow(signalBar, rates[1].low, true);
      lastSignalBar = signalBar;
      UpdateStatus("BUY SIGNAL", clrLime, rsi[2], adx[2]);
      return;
   }

   if(trendSell && rsiSellOK && adxStrong && confirmBear && spreadOk && atrOk && sessionOk)
   {
      EmitSignal("SELL", rates, rsi[2], adx[2]);
      DrawSignalArrow(signalBar, rates[1].high, false);
      lastSignalBar = signalBar;
      UpdateStatus("SELL SIGNAL", clrTomato, rsi[2], adx[2]);
      return;
   }

   UpdateStatus("WAITING", clrSilver, rsi[1], adx[1]);
}

//+------------------------------------------------------------------+
void DrawSignalArrow(datetime t, double price, bool isBuy)
{
   string name = "ALPHA_SIG_" + IntegerToString((int)t) + (isBuy ? "_B" : "_S");
   if(ObjectFind(0, name) >= 0)
      return;

   ObjectCreate(0, name, OBJ_ARROW, 0, t, price);
   ObjectSetInteger(0, name, OBJPROP_ARROWCODE, isBuy ? 241 : 242);
   ObjectSetInteger(0, name, OBJPROP_COLOR, isBuy ? clrLime : clrTomato);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, 2);
}

//+------------------------------------------------------------------+
bool CalcLevels(string side, MqlRates &rates[], double &entry, double &sl, double &tp)
{
   int idx = -1;
   entry = rates[1].close;

   if(side == "BUY")
   {
      idx = iLowest(tradeSymbol, InpTF, MODE_LOW, InpSwingLookback, 1);
      if(idx < 0) return false;
      sl = iLow(tradeSymbol, InpTF, idx);
      double risk = entry - sl;
      if(risk <= 0) return false;
      tp = entry + (InpRR * risk);
   }
   else
   {
      idx = iHighest(tradeSymbol, InpTF, MODE_HIGH, InpSwingLookback, 1);
      if(idx < 0) return false;
      sl = iHigh(tradeSymbol, InpTF, idx);
      double risk = sl - entry;
      if(risk <= 0) return false;
      tp = entry - (InpRR * risk);
   }

   int digits = (int)SymbolInfoInteger(tradeSymbol, SYMBOL_DIGITS);
   entry = NormalizeDouble(entry, digits);
   sl = NormalizeDouble(sl, digits);
   tp = NormalizeDouble(tp, digits);
   return true;
}

//+------------------------------------------------------------------+
void EmitSignal(string side, MqlRates &rates[], double rsiVal, double adxVal)
{
   double entry=0.0, sl=0.0, tp=0.0;
   if(!CalcLevels(side, rates, entry, sl, tp))
      return;

   string t = TimeToString(rates[1].time, TIME_DATE|TIME_MINUTES);
   string id = tradeSymbol + "-" + EnumToString(InpTF) + "-" + t + "-" + side;
   StringReplace(id, ":", "");
   StringReplace(id, ".", "");
   StringReplace(id, " ", "-");

   int digits = (int)SymbolInfoInteger(tradeSymbol, SYMBOL_DIGITS);
   string json = StringFormat("{\"id\":\"%s\",\"pair\":\"%s\",\"tf\":\"%s\",\"side\":\"%s\",\"entry\":%.*f,\"sl\":%.*f,\"tp\":%.*f,\"rr\":\"1:%.0f\",\"adx\":%.2f,\"rsi\":%.2f,\"signal_time\":\"%s\"}",
                              id, tradeSymbol, EnumToString(InpTF), side,
                              digits, entry, digits, sl, digits, tp,
                              InpRR, adxVal, rsiVal, t);

   Print("[AlphaLyceum] ", json);
   WriteSignal(json);
   ExecuteBacktestTrade(side, entry, sl, tp);
}

//+------------------------------------------------------------------+
void ExecuteBacktestTrade(string side, double entry, double sl, double tp)
{
   if(!InpEnableBacktestExecution) return;
   if(MQLInfoInteger(MQL_TESTER) == 0) return; // hanya saat Strategy Tester

   if(InpOnePositionOnly && PositionSelect(tradeSymbol))
      return;

   trade.SetExpertMagicNumber(8822001);
   trade.SetDeviationInPoints(50);

   double lot = CalculateLotByRisk(entry, sl);

   bool ok = false;
   if(side == "BUY")
      ok = trade.Buy(lot, tradeSymbol, 0.0, sl, tp, "ALPHA_BT_BUY");
   else
      ok = trade.Sell(lot, tradeSymbol, 0.0, sl, tp, "ALPHA_BT_SELL");

   if(!ok)
      Print("[AlphaLyceum][BT] order failed: ", trade.ResultRetcode(), " ", trade.ResultRetcodeDescription());
   else
      Print("[AlphaLyceum][BT] order placed: ", side, " lot=", DoubleToString(lot,2), " risk%=", DoubleToString(InpRiskPercent,2));
}

//+------------------------------------------------------------------+
bool IsSessionAllowed(datetime t)
{
   if(!InpUseSessionFilter) return true;

   MqlDateTime dt;
   TimeToStruct(t, dt);
   int h = dt.hour;

   if(InpSessionStartHour == InpSessionEndHour)
      return true;

   if(InpSessionStartHour < InpSessionEndHour)
      return (h >= InpSessionStartHour && h < InpSessionEndHour);

   // overnight session
   return (h >= InpSessionStartHour || h < InpSessionEndHour);
}

//+------------------------------------------------------------------+
double CalculateLotByRisk(double entry, double sl)
{
   if(!InpUseCompoundingRisk)
      return InpBacktestLot;

   double riskPrice = MathAbs(entry - sl);
   if(riskPrice <= 0.0)
      return InpBacktestLot;

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double riskMoney = equity * (InpRiskPercent / 100.0);

   double tickSize = SymbolInfoDouble(tradeSymbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue = SymbolInfoDouble(tradeSymbol, SYMBOL_TRADE_TICK_VALUE);
   if(tickSize <= 0 || tickValue <= 0)
      return InpBacktestLot;

   double ticksToSL = riskPrice / tickSize;
   double lossPerLot = ticksToSL * tickValue;
   if(lossPerLot <= 0)
      return InpBacktestLot;

   double rawLot = riskMoney / lossPerLot;

   double volStep = SymbolInfoDouble(tradeSymbol, SYMBOL_VOLUME_STEP);
   double volMin = SymbolInfoDouble(tradeSymbol, SYMBOL_VOLUME_MIN);
   double volMax = SymbolInfoDouble(tradeSymbol, SYMBOL_VOLUME_MAX);
   if(volStep <= 0) volStep = 0.01;

   double cappedMin = MathMax(volMin, InpMinLot);
   double cappedMax = MathMin(volMax, InpMaxLot);
   double lot = MathMax(cappedMin, MathMin(cappedMax, rawLot));
   lot = MathFloor(lot / volStep) * volStep;

   int volDigits = (int)MathRound(-MathLog10(volStep));
   if(volDigits < 0) volDigits = 2;
   return NormalizeDouble(lot, volDigits);
}

//+------------------------------------------------------------------+
void WriteSignal(string payload)
{
   int flags = FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_READ;
   if(InpUseCommonFile) flags |= FILE_COMMON;

   int handle = FileOpen(InpOutFile, flags);
   if(handle == INVALID_HANDLE)
   {
      Print("[AlphaLyceum] FileOpen failed: ", GetLastError());
      return;
   }

   FileSeek(handle, 0, SEEK_END);
   FileWriteString(handle, payload + "\n");
   FileClose(handle);
}

//+------------------------------------------------------------------+
void WriteBacktestMetrics()
{
   if(MQLInfoInteger(MQL_TESTER) == 0)
      return;

   string runId = InpRunId;
   if(StringLen(runId) == 0)
      runId = "manual";

   double netProfit = TesterStatistics(STAT_PROFIT);
   double pf = TesterStatistics(STAT_PROFIT_FACTOR);
   double trades = TesterStatistics(STAT_TRADES);
   double winrate = TesterStatistics(STAT_PROFIT_TRADES);
   double ddBal = TesterStatistics(STAT_BALANCE_DDREL_PERCENT);
   double ddEq = TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   double payoff = TesterStatistics(STAT_EXPECTED_PAYOFF);

   string line = StringFormat("%s,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f", runId, netProfit, pf, payoff, trades, ddBal, ddEq, winrate);

   string outFile = "alphalyceum_backtest_metrics.csv";
   int flags = FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_READ | FILE_COMMON;
   int h = FileOpen(outFile, flags);
   if(h == INVALID_HANDLE)
   {
      Print("[AlphaLyceum] metrics FileOpen failed: ", GetLastError());
      return;
   }

   if(FileSize(h) == 0)
      FileWriteString(h, "run_id,net_profit,profit_factor,expected_payoff,total_trades,balance_dd_rel_pct,equity_dd_rel_pct,winrate_pct\n");

   FileSeek(h, 0, SEEK_END);
   FileWriteString(h, line + "\n");
   FileClose(h);
}

void OnTesterDeinit()
{
   WriteBacktestMetrics();
}

double GetBufferValue(int handle, int bufferIndex, int shift)
{
   double v[];
   ArraySetAsSeries(v, true);
   if(CopyBuffer(handle, bufferIndex, shift, 1, v) < 1)
      return 0.0;
   return v[0];
}
//+------------------------------------------------------------------+
