# Copyright 2023 The Qwen team, Alibaba Group. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import math
from typing import Dict, Optional, Union

from qwen_agent.tools.base import BaseTool, register_tool


def _check_yfinance_installed():
    try:
        import yfinance  # noqa
    except ImportError as e:
        raise ImportError(
            'yfinance is required for the Finance tool. '
            'Please install it by running: pip install yfinance'
        ) from e


def _safe_int(value, default=0):
    """Safely convert value to int, handling NaN and None."""
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        return int(value)
    except (ValueError, TypeError):
        return default


@register_tool('finance')
class Finance(BaseTool):
    description = (
        'A financial data tool that retrieves real-time and historical stock market data. '
        'It can fetch stock prices, company information, historical data, and key financial metrics. '
        'Use this tool when users ask about stock prices, market data, or company financials.'
    )
    parameters = {
        'type': 'object',
        'properties': {
            'symbol': {
                'description': (
                    'The stock ticker symbol (e.g., "AAPL" for Apple, "GOOGL" for Google, '
                    '"MSFT" for Microsoft, "BABA" for Alibaba, "9988.HK" for Alibaba HK). '
                    'For Chinese A-shares, use format like "600519.SS" (Shanghai) or "000001.SZ" (Shenzhen).'
                ),
                'type': 'string',
            },
            'action': {
                'description': (
                    'The type of data to retrieve. Options: '
                    '"price" - Get current stock price and basic info; '
                    '"history" - Get historical price data; '
                    '"info" - Get detailed company information; '
                    '"financials" - Get financial statements summary.'
                ),
                'type': 'string',
                'enum': ['price', 'history', 'info', 'financials'],
            },
            'period': {
                'description': (
                    'Time period for historical data (only used when action="history"). '
                    'Options: "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max". '
                    'Default is "1mo".'
                ),
                'type': 'string',
            },
        },
        'required': ['symbol', 'action'],
    }

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        _check_yfinance_installed()

    def call(self, params: Union[str, dict], **kwargs) -> str:
        params = self._verify_json_format_args(params)

        symbol = params['symbol'].upper().strip()
        action = params['action'].lower().strip()
        period = params.get('period', '1mo')

        import yfinance as yf

        try:
            ticker = yf.Ticker(symbol)

            if action == 'price':
                return self._get_price(ticker, symbol)
            elif action == 'history':
                return self._get_history(ticker, symbol, period)
            elif action == 'info':
                return self._get_info(ticker, symbol)
            elif action == 'financials':
                return self._get_financials(ticker, symbol)
            else:
                return f'Unknown action: {action}. Please use one of: price, history, info, financials.'

        except Exception as e:
            return f'Error retrieving data for {symbol}: {str(e)}'

    def _get_price(self, ticker, symbol: str) -> str:
        """Get current stock price and basic trading info."""
        try:
            info = ticker.info
            fast_info = ticker.fast_info

            result = {
                'symbol': symbol,
                'name': info.get('shortName', info.get('longName', 'N/A')),
                'current_price': fast_info.get('lastPrice', info.get('currentPrice', 'N/A')),
                'previous_close': info.get('previousClose', fast_info.get('previousClose', 'N/A')),
                'open': info.get('open', fast_info.get('open', 'N/A')),
                'day_high': info.get('dayHigh', fast_info.get('dayHigh', 'N/A')),
                'day_low': info.get('dayLow', fast_info.get('dayLow', 'N/A')),
                'volume': info.get('volume', fast_info.get('lastVolume', 'N/A')),
                'market_cap': info.get('marketCap', fast_info.get('marketCap', 'N/A')),
                'currency': info.get('currency', 'N/A'),
            }

            # Calculate change
            if result['current_price'] != 'N/A' and result['previous_close'] != 'N/A':
                try:
                    change = float(result['current_price']) - float(result['previous_close'])
                    change_pct = (change / float(result['previous_close'])) * 100
                    result['change'] = round(change, 2)
                    result['change_percent'] = f'{change_pct:.2f}%'
                except (ValueError, TypeError, ZeroDivisionError):
                    pass

            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            return f'Error getting price for {symbol}: {str(e)}'

    def _get_history(self, ticker, symbol: str, period: str) -> str:
        """Get historical price data."""
        try:
            valid_periods = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max']
            if period not in valid_periods:
                period = '1mo'

            hist = ticker.history(period=period)

            if hist.empty:
                return f'No historical data available for {symbol}.'

            # Format the data
            records = []
            for date, row in hist.tail(20).iterrows():  # Last 20 records to avoid too much data
                records.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'open': round(row['Open'], 2),
                    'high': round(row['High'], 2),
                    'low': round(row['Low'], 2),
                    'close': round(row['Close'], 2),
                    'volume': _safe_int(row['Volume']),
                })

            result = {
                'symbol': symbol,
                'period': period,
                'total_records': len(hist),
                'showing_last': min(20, len(hist)),
                'data': records,
            }

            # Add summary statistics
            result['summary'] = {
                'period_high': round(hist['High'].max(), 2),
                'period_low': round(hist['Low'].min(), 2),
                'avg_volume': _safe_int(hist['Volume'].mean()),
                'start_price': round(hist['Close'].iloc[0], 2),
                'end_price': round(hist['Close'].iloc[-1], 2),
            }

            # Calculate period return
            try:
                period_return = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
                result['summary']['period_return'] = f'{period_return:.2f}%'
            except (ZeroDivisionError, IndexError):
                pass

            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            return f'Error getting history for {symbol}: {str(e)}'

    def _get_info(self, ticker, symbol: str) -> str:
        """Get detailed company information."""
        try:
            info = ticker.info

            result = {
                'symbol': symbol,
                'name': info.get('longName', info.get('shortName', 'N/A')),
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'country': info.get('country', 'N/A'),
                'website': info.get('website', 'N/A'),
                'description': info.get('longBusinessSummary', 'N/A'),
                'employees': info.get('fullTimeEmployees', 'N/A'),
                'market_cap': info.get('marketCap', 'N/A'),
                'enterprise_value': info.get('enterpriseValue', 'N/A'),
                'pe_ratio': info.get('trailingPE', 'N/A'),
                'forward_pe': info.get('forwardPE', 'N/A'),
                'peg_ratio': info.get('pegRatio', 'N/A'),
                'price_to_book': info.get('priceToBook', 'N/A'),
                'dividend_yield': info.get('dividendYield', 'N/A'),
                'beta': info.get('beta', 'N/A'),
                '52_week_high': info.get('fiftyTwoWeekHigh', 'N/A'),
                '52_week_low': info.get('fiftyTwoWeekLow', 'N/A'),
                'avg_volume': info.get('averageVolume', 'N/A'),
                'currency': info.get('currency', 'N/A'),
            }

            # Format dividend yield as percentage
            if result['dividend_yield'] != 'N/A' and result['dividend_yield'] is not None:
                # Handle potential 100x errors from Yahoo Finance data
                # If yield is > 1 (100%), it's likely already a percentage or an error
                # Typical yields are 0.01 to 0.10 (1% to 10%)
                val = float(result['dividend_yield'])
                if val > 1:
                    result['dividend_yield'] = f'{val:.2f}%'
                else:
                    result['dividend_yield'] = f'{val * 100:.2f}%'

            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            return f'Error getting info for {symbol}: {str(e)}'

    def _get_financials(self, ticker, symbol: str) -> str:
        """Get financial statements summary."""
        try:
            info = ticker.info

            result = {
                'symbol': symbol,
                'name': info.get('shortName', 'N/A'),
                'currency': info.get('financialCurrency', info.get('currency', 'N/A')),
                'revenue': {
                    'total_revenue': info.get('totalRevenue', 'N/A'),
                    'revenue_per_share': info.get('revenuePerShare', 'N/A'),
                    'revenue_growth': info.get('revenueGrowth', 'N/A'),
                },
                'profitability': {
                    'gross_profit': info.get('grossProfits', 'N/A'),
                    'gross_margin': info.get('grossMargins', 'N/A'),
                    'operating_margin': info.get('operatingMargins', 'N/A'),
                    'profit_margin': info.get('profitMargins', 'N/A'),
                    'ebitda': info.get('ebitda', 'N/A'),
                    'net_income': info.get('netIncomeToCommon', 'N/A'),
                },
                'per_share': {
                    'earnings_per_share': info.get('trailingEps', 'N/A'),
                    'forward_eps': info.get('forwardEps', 'N/A'),
                    'book_value': info.get('bookValue', 'N/A'),
                },
                'balance_sheet': {
                    'total_cash': info.get('totalCash', 'N/A'),
                    'total_debt': info.get('totalDebt', 'N/A'),
                    'debt_to_equity': info.get('debtToEquity', 'N/A'),
                    'current_ratio': info.get('currentRatio', 'N/A'),
                    'quick_ratio': info.get('quickRatio', 'N/A'),
                },
                'cash_flow': {
                    'operating_cash_flow': info.get('operatingCashflow', 'N/A'),
                    'free_cash_flow': info.get('freeCashflow', 'N/A'),
                },
                'returns': {
                    'return_on_assets': info.get('returnOnAssets', 'N/A'),
                    'return_on_equity': info.get('returnOnEquity', 'N/A'),
                },
            }

            # Format percentages
            for category in ['revenue', 'profitability', 'returns']:
                for key, value in result[category].items():
                    if value != 'N/A' and value is not None:
                        if 'margin' in key.lower() or 'growth' in key.lower() or 'return' in key.lower():
                            try:
                                result[category][key] = f'{float(value) * 100:.2f}%'
                            except (ValueError, TypeError):
                                pass

            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            return f'Error getting financials for {symbol}: {str(e)}'
