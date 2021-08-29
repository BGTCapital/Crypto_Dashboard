import threading

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import pandas
import plotly.express as px
from dash.dependencies import Input, Output
from cryptofeed_worker import OrderBook, start_feed, TimeKeeper

# Object which acts as the carrier through the app and is passed between child threads

btcBookObject = OrderBook('btc',
                          'BTC-USD',
                          'BTC',
                          "BTC-USD Depth Chart using cryptofeed and Dash",
                          'BTC-USD Live Depth Chart')

ethBookObject = OrderBook('eth',
                          'ETH-USD',
                          'ETH',
                          "ETH-USD Depth Chart using cryptofeed and Dash",
                          'ETH-USD Live Depth Chart')

adaBookObject = OrderBook('ada',
                          'ADA-USD',
                          'ADA',
                          "ADA-USD Depth Chart using cryptofeed and Dash",
                          'ADA-USD Live Depth Chart')

timeKeeperObject = TimeKeeper()


# Function which holds the Dash web server and starts the web server
def run_server():
    base_trade = [({'Currency Pair': 'BTC-USD', 'Side': 'bid', 'Amount': '100', 'Price': '3000'})]

    base_df = pandas.DataFrame(base_trade)

    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

    app = dash.Dash(__name__, external_stylesheets=external_stylesheets, update_title=None)
    app.layout = html.Div(
        html.Div([
            html.Div([html.H4('ETH-USD Live Depth Chart', id='header',
                              style={'float': 'left'}), html.H4('Session stats', id='stats',
                                                                style={'float': 'right', 'display': 'inline-block'})]),
            # FIXME - left off here
            html.Div(id='live-update-text'),
            html.Div([dcc.Dropdown(
                id='token-selector',
                options=[
                    {'label': 'BTC', 'value': 'BTC-USD'},
                    {'label': 'ETH', 'value': 'ETH-USD'},
                    {'label': 'ADA', 'value': 'ADA-USD'}
                ],
                style={'width': '50vw'}
            ),
                html.Output(
                    id='statsBox',
                    children=['Time elapsed'],
                    style={'width': '25vw', 'float': 'right'}
                )]),
            dcc.Graph(id='live-update-graph',
                      figure=px.ecdf(ethBookObject.get_asks(), x='ETH-USD Price', y="size", ecdfnorm=None, color="side",
                                     labels={
                                         "size": "ETH",
                                         "side": "Side",
                                         "value": "ETH-USD Price"
                                     },
                                     title="ETH-USD Depth Chart using cryptofeed and Dash"),
                      style={'width': '50vw', 'border': '2px black solid'}),
            dash_table.DataTable(
                id='trade_table',
                columns=[{"name": i, "id": i} for i in base_df],
                data=base_df.to_dict('records'),
                style_cell={'textAlign': 'center'},
                style_table={'width': '50vw'}
            ),
            dcc.Interval(
                id='interval-component',
                interval=1 * 500,  # Updates every half a second
                n_intervals=0
            ),
            dcc.Interval(
                id='stats-interval',
                interval=1 * 50,
                n_intervals=0
            )
        ])
    )

    @app.callback(Output('statsBox', "children"),
                  [Input('stats-interval', 'n_intervals'),
                   Input('token-selector', 'value')])
    def update_stats(n, value):
        return timeKeeperObject.get_time_elapse()

    #FIXME - should do faster callback interval with for time elapsed

    # Callback to update the graph with any updates to the L2 Book
    @app.callback([Output('live-update-graph', 'figure'),
                   Output('header', 'children'),
                   Output('trade_table', "data")],
                  [Input('interval-component', 'n_intervals'),
                   Input('token-selector', 'value')])
    def update_graph(n, value):
        # Layout the graph
        # BTC
        if value == 'BTC-USD':
            return build_graph(btcBookObject)
        elif value == 'ETH-USD':
            return build_graph(ethBookObject)
        elif value == 'ADA-USD':
            return build_graph(adaBookObject)
        else:
            return build_graph(ethBookObject)

    # Run DASH server
    app.run_server()


def build_graph(order_book):
    fig = px.ecdf(order_book.get_asks(), x=order_book.get_symbol(), y="size", ecdfnorm=None, color="side",
                  labels={
                      "size": order_book.get_size(),
                      "side": "Side",
                      "value": order_book.get_symbol()
                  },
                  title=order_book.get_title())
    fig.data[0].line.color = 'rgb(255, 160, 122)'  # red
    fig.data[0].line.width = 5

    # Opposing side of the graph
    fig2 = px.ecdf(order_book.get_bids(), x=order_book.get_symbol(), y="size", ecdfmode='reversed', ecdfnorm=None,
                   color="side")
    fig2.data[0].line.color = 'rgb(34, 139, 34)'  # green
    fig2.data[0].line.width = 5

    # Merge the figures together
    fig.add_trace(fig2.data[0])

    # Display the mid-market price
    fig.add_vline(x=order_book.mid_market,
                  annotation_text='Mid-Market Price: ' + "{:.2f}".format(order_book.mid_market),
                  annotation_position='top')

    new_df = pandas.DataFrame(order_book.trade_list)

    return fig, order_book.get_subtitle(), new_df.to_dict('records')


if __name__ == "__main__":
    # Start threading for both the cryptofeed worker and web server
    # Cryptofeed thread takes the global carrier object as a parameter which is passed in as a callback
    # This object is then passed back and forth between cryptofeed and the webserver
    t1 = threading.Thread(target=start_feed, args=[btcBookObject, ethBookObject, adaBookObject])
    t1.start()

    # Web server thread
    t2 = threading.Thread(target=run_server)
    t2.start()