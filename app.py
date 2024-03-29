import flask
from flask import Flask, render_template, request # for web app
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
import pandas as pd
import yfinance
import plotly
import plotly.express as px
import json # for graph plotting in website
# NLTK VADER for sentiment analysis
import nltk
nltk.downloader.download('vader_lexicon')
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import datetime 
import dateutil.relativedelta as rd

# for extracting data from finviz
finviz_url = 'https://finviz.com/quote.ashx?t='

def get_news(ticker):
    url = finviz_url + ticker
    req = Request(url=url,headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0'}) 
    response = urlopen(req)    
    # Read the contents of the file into 'html'
    html = BeautifulSoup(response)
    # Find 'news-table' in the Soup and load it into 'news_table'
    news_table = html.find(id='news-table')
    return news_table
	
# parse news into dataframe
def parse_news(news_table):
    parsed_news = []
    
    for x in news_table.findAll('tr'):
        # read the text from each tr tag into text
        # get text from a only
        text = x.a.get_text() 
        # splite text in the td tag into a list 
        date_scrape = x.td.text.split()
        # if the length of 'date_scrape' is 1, load 'time' as the only element
        
        if len(date_scrape) == 1:
            time = date_scrape[0]
            scrapedurl = x.find("a", {"class": "tab-link-news"})
            
        # else load 'date' as the 1st element and 'time' as the second    
        else:
            date = date_scrape[0]
            time = date_scrape[1]
            scrapedurl = x.find("a", {"class": "tab-link-news"})
        
        # Append ticker, date, time and headline as a list to the 'parsed_news' list
        parsed_news.append([date, time, text])
        #scrapedurl['href']
        
        # Set column names
        columns = ['date', 'time', 'headline']
        #'url'

        # Convert the parsed_news list into a DataFrame called 'parsed_and_scored_news'
        parsed_news_df = pd.DataFrame(parsed_news, columns=columns)
        
        # Create a pandas datetime object from the strings in 'date' and 'time' column
        parsed_news_df['datetime'] = pd.to_datetime(parsed_news_df['date'] + ' ' + parsed_news_df['time'])
    
    return parsed_news_df
        
def score_news(parsed_news_df):
    # Instantiate the sentiment intensity analyzer
    vader = SentimentIntensityAnalyzer()
    
    # Iterate through the headlines and get the polarity scores using vader
    scores = parsed_news_df['headline'].apply(vader.polarity_scores).tolist()

    #parsed_news_df_headline = "<a href='"parsed_news_df['url']+"'>"+parsed_news_df['headline']+"</a>"

    # Convert the 'scores' list of dicts into a DataFrame
    scores_dffff = pd.DataFrame(scores)
    scores_df = scores_dffff.round(2)

    # Join the DataFrames of the news and the list of dicts
    parsed_and_scored_news = parsed_news_df.join(scores_df, rsuffix='_right')
    
            
    parsed_and_scored_news = parsed_and_scored_news.set_index('datetime')
    
    parsed_and_scored_news = parsed_and_scored_news.drop(['date', 'time'], 1)    
        
    parsed_and_scored_news = parsed_and_scored_news.rename(columns={"compound": "score"})

    return parsed_and_scored_news

def plot_hourly_sentiment(parsed_and_scored_news, ticker):
   
    # Group by date and ticker columns from scored_news and calculate the mean
    mean_scores = parsed_and_scored_news.resample('H').mean()

    # Plot a bar chart with plotly
    fig = px.bar(mean_scores, x=mean_scores.index, y='score', title = ticker + ' Hourly Sentiment Scores')
    return fig

def plot_daily_sentiment(parsed_and_scored_news, ticker):
   
    # Group by date and ticker columns from scored_news and calculate the mean
    mean_scores = parsed_and_scored_news.resample('D').mean()

    # Plot a bar chart with plotly
    fig = px.bar(mean_scores, x=mean_scores.index, y='score', title = ticker + ' Daily Sentiment Scores')
    return fig

def get_prices(ticker):
#    # Get opening prices from yfinance
    # Date settings
    now = datetime.datetime.now()
    month = now + rd.relativedelta(months=-1)

    stock_data = yfinance.download(ticker,start=month, end=now)

    columnz = ['Open', 'Low', 'Close', 'Adj Close', 'Volume']

    parsed_price_df = pd.DataFrame(stock_data, columns=columnz)

    # Rounded 2
    parsed_price_df = parsed_price_df.round(2)

    #fig = px.box(data, x=data.index, y='Open', title = ticker + ' Daily Stock Prices')

    return parsed_price_df


app = Flask(__name__)



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/stock', methods = ['POST'])

def stock():
    ticker = flask.request.form['ticker'].upper()
    news_table = get_news(ticker)
    parsed_news_df = parse_news(news_table)
    parsed_and_scored_news = score_news(parsed_news_df)
    fig_hourly = plot_hourly_sentiment(parsed_and_scored_news, ticker)
    fig_daily = plot_daily_sentiment(parsed_and_scored_news, ticker)
    parsed_price_df = get_prices(ticker)
    graphJSON_hourly = json.dumps(fig_hourly, cls=plotly.utils.PlotlyJSONEncoder)
    graphJSON_daily = json.dumps(fig_daily, cls=plotly.utils.PlotlyJSONEncoder)
    header= "{}".format(ticker)
    description = """{}""".format(ticker)
    return render_template('stock.html',graphJSON_hourly=graphJSON_hourly, graphJSON_daily=graphJSON_daily, header=header,table=parsed_and_scored_news.to_html(classes='data'),tableprice=parsed_price_df.to_html(classes='data'),description=description)


###############WORKING ON IT
@app.route('/stock/<int:ticker>/')
def show_post(ticker):
    return render_template('details.html')

@app.route('/params/')
def params():
    param = request.args.get('some_param')
    if param:
        return param
    else:
        return "bad request :(", 400  # handle missing param as 400 error
        
if __name__ == '__main__':
    app.run()