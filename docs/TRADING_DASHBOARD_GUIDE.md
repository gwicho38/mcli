# Trading Dashboard Guide

## Overview

The MCLI Trading Dashboard is a comprehensive trading platform that connects politician trading data with Alpaca Trading API to enable data-driven trading decisions. The system supports both paper trading for testing and live trading for real money.

## Features

### 🎯 Core Trading Features

1. **Portfolio Management**
   - Create and manage multiple portfolios
   - Track portfolio performance in real-time
   - Support for test, paper, and live trading accounts

2. **Order Execution**
   - Market and limit orders
   - Real-time order status tracking
   - Integration with Alpaca Trading API

3. **Position Management**
   - Real-time position tracking
   - P&L calculation and monitoring
   - Position sizing and risk management

4. **Paper Trading**
   - Test strategies without real money
   - Market simulation capabilities
   - Historical backtesting

### 📊 Analytics & Monitoring

1. **Performance Tracking**
   - Portfolio performance metrics
   - Risk analysis (Sharpe ratio, max drawdown, volatility)
   - Historical performance charts

2. **Trading Signals**
   - ML-generated trading signals
   - Signal confidence and strength scoring
   - Automated signal tracking

3. **Risk Management**
   - Position size limits
   - Portfolio risk controls
   - Real-time risk monitoring

## Getting Started

### 1. Setup Alpaca Account

1. Sign up for an Alpaca account at [alpaca.markets](https://alpaca.markets)
2. Get your API credentials (API Key and Secret Key)
3. Configure your account in the Trading Settings page

### 2. Create Your First Portfolio

1. Navigate to the **Trading Dashboard** page
2. Go to the **Portfolios** tab
3. Click **Create New Portfolio**
4. Fill in portfolio details:
   - Portfolio Name
   - Initial Capital
   - Account Type (Test/Paper/Live)

### 3. Start Paper Trading

1. Go to the **Test Portfolio** page
2. Click **Create Test Portfolio** if you don't have one
3. Use the paper trading interface to:
   - Place test orders
   - Monitor positions
   - Simulate market movements

## Dashboard Pages

### 📈 Trading Dashboard

Main trading interface with:
- Portfolio overview and metrics
- Order placement interface
- Position monitoring
- Recent activity tracking

### 🧪 Test Portfolio

Paper trading environment featuring:
- Test order execution
- Market simulation
- Backtesting capabilities
- Performance analysis

### ⚙️ Settings

Configuration options for:
- Alpaca API credentials
- Risk management parameters
- Portfolio alerts
- Trading preferences

## Trading Workflow

### 1. Data Collection
- Politician trading data is automatically collected
- ML models analyze patterns and generate signals
- Signals are stored in the database

### 2. Signal Analysis
- Review generated trading signals
- Analyze confidence and strength scores
- Consider risk factors and market conditions

### 3. Order Placement
- Use the trading interface to place orders
- Choose between market and limit orders
- Set position sizes based on risk management rules

### 4. Monitoring
- Track order execution status
- Monitor position performance
- Review portfolio metrics

### 5. Risk Management
- Monitor position sizes
- Track portfolio risk metrics
- Adjust positions as needed

## API Integration

### Alpaca Trading API

The system integrates with Alpaca's trading API for:
- Order execution
- Position management
- Account information
- Market data

### Configuration

Set up your Alpaca credentials in the Settings page:
- API Key
- Secret Key
- Environment (Paper/Live)
- Base URL

## Risk Management

### Position Sizing
- Maximum position size per stock (default: 10% of portfolio)
- Maximum portfolio risk (default: 20%)
- Dynamic position sizing based on signal strength

### Risk Metrics
- Value at Risk (VaR)
- Conditional Value at Risk (CVaR)
- Maximum drawdown tracking
- Volatility monitoring

### Alerts
- Position size warnings
- Risk threshold breaches
- Performance alerts
- Signal notifications

## Performance Analytics

### Key Metrics
- Total Return
- Annualized Return
- Sharpe Ratio
- Sortino Ratio
- Maximum Drawdown
- Volatility

### Charts
- Portfolio value over time
- Daily returns
- Position allocation
- Risk metrics

## Best Practices

### 1. Start with Paper Trading
- Test your strategies with paper money first
- Use the backtesting feature to validate approaches
- Simulate different market conditions

### 2. Risk Management
- Never risk more than you can afford to lose
- Use position sizing to limit individual stock exposure
- Monitor portfolio risk metrics regularly

### 3. Signal Analysis
- Review signal confidence and strength
- Consider multiple signals before trading
- Understand the underlying data and methodology

### 4. Regular Monitoring
- Check portfolio performance daily
- Review and adjust positions as needed
- Monitor for any system alerts

## Troubleshooting

### Common Issues

1. **API Connection Errors**
   - Verify Alpaca credentials
   - Check network connectivity
   - Ensure API keys are valid

2. **Order Execution Failures**
   - Check market hours
   - Verify sufficient buying power
   - Review order parameters

3. **Data Sync Issues**
   - Refresh portfolio data
   - Check Alpaca account status
   - Verify API permissions

### Support

For technical support:
- Check the system logs
- Review error messages
- Contact system administrator

## Security

### API Security
- API keys are encrypted in the database
- Credentials are never logged
- Secure transmission protocols

### Data Protection
- Portfolio data is encrypted
- User access controls
- Audit logging

## Future Enhancements

Planned features include:
- Advanced order types (stop-loss, take-profit)
- Automated trading strategies
- More sophisticated risk models
- Integration with additional brokers
- Mobile app support

## Conclusion

The MCLI Trading Dashboard provides a powerful platform for data-driven trading based on politician trading insights. Start with paper trading to test your strategies, then gradually move to live trading as you gain confidence and experience.

Remember: Trading involves risk, and past performance does not guarantee future results. Always trade responsibly and within your risk tolerance.