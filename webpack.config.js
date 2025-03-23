// webpack.config.js
const path = require('path');

module.exports = {
  entry: './static/js/components/WaterBillPaymentPortal.jsx',
  output: {
    filename: 'payment-portal-bundle.js',
    path: path.resolve(__dirname, 'static/js/dist'),
    library: 'WaterBillPaymentPortal',
    libraryTarget: 'var'
  },
  module: {
    rules: [
      {
        test: /\.(js|jsx)$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: ['@babel/preset-env', '@babel/preset-react']
          }
        }
      }
    ]
  },
  resolve: {
    extensions: ['.js', '.jsx']
  }
};