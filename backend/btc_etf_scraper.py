#!/usr/bin/env python3
"""
Bitcoin ETF Flow Data Scraper
Fetches and cleans daily ETF flow data from Farside Investors
"""

import pandas as pd
import re
from datetime import datetime
import json
import time


class BTCETFScraper:
    """Scraper for Bitcoin ETF flow data from Farside Investors"""
    
    def __init__(self):
        self.url = "https://farside.co.uk/bitcoin-etf-flow-all-data/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
    
    def fetch_data(self):
        """Fetch the HTML content from Farside Investors using cloudscraper"""
        print(f"Fetching data from {self.url}...")
        
        # Try with cloudscraper first (bypasses Cloudflare)
        try:
            import cloudscraper
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'darwin',
                    'desktop': True
                }
            )
            print("Using cloudscraper to bypass anti-bot protection...")
            response = scraper.get(self.url, timeout=30)
            response.raise_for_status()
            print(f"✓ Successfully fetched data with cloudscraper (Status: {response.status_code})")
            return response.text
        except ImportError:
            print("⚠ cloudscraper not found, trying requests with enhanced headers...")
            pass
        except Exception as e:
            print(f"⚠ cloudscraper failed: {e}, falling back to requests...")
        
        # Fallback to requests with retry logic
        try:
            import requests
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    print(f"Attempt {attempt + 1}/{max_retries}...")
                    time.sleep(attempt * 2)  # Exponential backoff
                    
                    session = requests.Session()
                    session.headers.update(self.headers)
                    response = session.get(self.url, timeout=30)
                    response.raise_for_status()
                    print(f"✓ Successfully fetched data (Status: {response.status_code})")
                    return response.text
                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        raise
                    print(f"Retry {attempt + 1} failed: {e}")
        except Exception as e:
            print(f"✗ All fetch methods failed: {e}")
            print("\n💡 SOLUTION: Install cloudscraper to bypass protection:")
            print("   pip install cloudscraper")
            raise
    
    def clean_value(self, value):
        """
        Clean individual cell values
        - Convert (15.4) to -15.4
        - Remove $, commas
        - Handle empty/NaN as 0
        """
        if pd.isna(value) or value == '' or value == '-' or value == '—':
            return 0.0
        
        # Convert to string for processing
        value_str = str(value).strip()
        
        # Handle parentheses (negative numbers)
        if '(' in value_str and ')' in value_str:
            # Extract number from parentheses and make negative
            value_str = '-' + value_str.replace('(', '').replace(')', '')
        
        # Remove dollar signs and commas
        value_str = value_str.replace('$', '').replace(',', '')
        
        try:
            return float(value_str)
        except ValueError:
            # If conversion fails, return the original string (likely a date or ticker)
            return value_str
    
    def parse_html_table(self, html_content):
        """Parse HTML tables using pandas"""
        print("Parsing HTML tables...")
        try:
            # Read all tables from the HTML
            tables = pd.read_html(html_content)
            
            if not tables:
                raise ValueError("No tables found in the HTML content")
            
            # The main table is usually the first or largest one
            # Let's find the table with the most columns (ETF flow table)
            main_table = max(tables, key=lambda x: len(x.columns))
            print(f"✓ Found table with {len(main_table)} rows and {len(main_table.columns)} columns")
            
            return main_table
        except Exception as e:
            print(f"✗ Error parsing HTML tables: {e}")
            raise
    
    def clean_dataframe(self, df):
        """Clean and format the DataFrame"""
        print("Cleaning data...")
        
        # Make a copy to avoid modifying original
        df_clean = df.copy()
        
        # Get column names
        print(f"Original columns: {list(df_clean.columns)}")
        
        # The first column is usually the Date
        date_col = df_clean.columns[0]
        
        # Clean date column
        df_clean[date_col] = df_clean[date_col].apply(lambda x: self.clean_date(x))
        
        # Rename date column for clarity
        df_clean = df_clean.rename(columns={date_col: 'Date'})
        
        # Clean all numerical columns (everything except Date)
        for col in df_clean.columns:
            if col != 'Date':
                df_clean[col] = df_clean[col].apply(self.clean_value)
        
        # Remove rows where Date is invalid
        df_clean = df_clean[df_clean['Date'].notna()]
        df_clean = df_clean[df_clean['Date'] != 0.0]
        
        # Reset index
        df_clean = df_clean.reset_index(drop=True)
        
        print(f"✓ Cleaned {len(df_clean)} rows of data")
        return df_clean
    
    def clean_date(self, date_str):
        """Convert date string to YYYY-MM-DD format"""
        if pd.isna(date_str) or date_str == '' or date_str == '-':
            return None
        
        date_str = str(date_str).strip()
        
        # Try different date formats
        date_formats = [
            '%d %b %Y',      # 30 Dec 2024
            '%d %B %Y',      # 30 December 2024
            '%Y-%m-%d',      # 2024-12-30
            '%m/%d/%Y',      # 12/30/2024
            '%d/%m/%Y',      # 30/12/2024
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # If no format matches, return original
        print(f"Warning: Could not parse date: {date_str}")
        return date_str
    
    def get_flow_summary(self, df):
        """
        获取每日和每周的 BTC ETF 流向汇总
        返回适合放入 main.py 的中文描述
        """
        # 过滤掉统计行 (Total, Average, Maximum, Minimum)
        df_filtered = df[~df['Date'].isin(['Total', 'Average', 'Maximum', 'Minimum'])]
        df_filtered = df_filtered[df_filtered['Date'].notna()]
        
        if len(df_filtered) == 0:
            return "数据不可用"
        
        # 获取最后一天的数据
        last_row = df_filtered.iloc[-1]
        last_date = last_row['Date']
        
        # 找到 Total 列
        total_col = None
        for col in df.columns:
            if 'total' in col.lower() or col == 'Total':
                total_col = col
                break
        
        if total_col is None:
            return "数据格式错误"
        
        last_day_flow = last_row[total_col]
        
        # 获取最近 5 个交易日的汇总
        recent_5_days = df_filtered.tail(5)
        total_5_days = recent_5_days[total_col].sum()
        
        # 格式化输出
        if last_day_flow > 0:
            daily_desc = f"单日流入 ${abs(last_day_flow):.1f}M"
        elif last_day_flow < 0:
            daily_desc = f"单日流出 ${abs(last_day_flow):.1f}M"
        else:
            daily_desc = "无明显流动"
        
        if total_5_days > 1000:
            weekly_desc = f"单周流入超 ${abs(total_5_days)/1000:.2f}B"
        elif total_5_days > 0:
            weekly_desc = f"近5日累计流入 ${abs(total_5_days):.1f}M"
        elif total_5_days < -2000:
            weekly_desc = f"单周流出超 ${abs(total_5_days)/1000:.2f}B"
        elif total_5_days < -500:
            weekly_desc = f"近5日累计流出 ${abs(total_5_days):.1f}M"
        else:
            weekly_desc = "近5日小幅波动"
        
        return f"{daily_desc}; {weekly_desc}"
    
    def save_to_json(self, df, filename='btc_etf_flows.json'):
        """Save DataFrame to JSON file"""
        print(f"Saving data to {filename}...")
        try:
            # Convert DataFrame to dict with records orientation
            data_dict = df.to_dict(orient='records')
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data_dict, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Data saved to {filename}")
        except Exception as e:
            print(f"✗ Error saving to JSON: {e}")
            raise
    
    def run(self):
        """Main execution method"""
        print("=" * 60)
        print("Bitcoin ETF Flow Data Scraper")
        print("=" * 60)
        
        # Step 1: Fetch HTML
        html_content = self.fetch_data()
        
        # Step 2: Parse table
        raw_df = self.parse_html_table(html_content)
        
        # Step 3: Clean data
        clean_df = self.clean_dataframe(raw_df)
        
        # Step 4: Display last 5 rows
        print("\n" + "=" * 60)
        print("LAST 5 DAYS OF DATA:")
        print("=" * 60)
        print(clean_df.tail(5).to_string(index=False))
        
        # Step 5: Save to JSON
        print("\n" + "=" * 60)
        self.save_to_json(clean_df)
        
        print("=" * 60)
        print("✓ Scraping complete!")
        print("=" * 60)
        
        return clean_df


def main():
    """Entry point"""
    scraper = BTCETFScraper()
    df = scraper.run()
    
    # Additional analysis
    print("\n" + "=" * 60)
    print("DATA SUMMARY:")
    print("=" * 60)
    print(f"Total days: {len(df)}")
    print(f"Date range: {df['Date'].iloc[0]} to {df['Date'].iloc[-1]}")
    
    # Find Total column if it exists
    total_cols = [col for col in df.columns if 'total' in col.lower() or 'net' in col.lower()]
    if total_cols:
        total_col = total_cols[0]
        print(f"\nTotal Net Flow Statistics:")
        print(f"  Mean: ${df[total_col].mean():.2f}M")
        print(f"  Recent 5-day total: ${df[total_col].tail(5).sum():.2f}M")
        print(f"  Last day: ${df[total_col].iloc[-1]:.2f}M")


if __name__ == "__main__":
    main()
