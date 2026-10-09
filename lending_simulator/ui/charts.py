"""Consistent axes, identities, and full-resolution analytical figures."""

from datetime import date

import plotly.graph_objects as go
import streamlit as st

from lending_simulator.presentation import monthly_frame
from lending_simulator.ui.data import profit_bridge
from lending_simulator.ui.theme import FONT, INK, MUTED, TEAL
from lending_simulator.ui.formatting import money


def dates(result):
    year, month = map(int, result.manifest()['start_month'].split('-'))
    ordinal = year * 12 + month - 1
    return [date((ordinal + row.month) // 12, (ordinal + row.month) % 12 + 1, 1)
            for row in result.monthly]


def style(fig, height=330):
    fig.update_layout(height=height, margin=dict(l=10, r=18, t=34, b=25),
        font=dict(family=FONT, size=14, color=INK), paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)', hovermode='x unified',
        legend=dict(orientation='h', y=1.14, x=0, font=dict(size=13)))
    fig.update_xaxes(showgrid=False, automargin=True, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor='#DFE6ED', zerolinecolor='#8799A8', automargin=True,
                     tickfont=dict(color=MUTED))
    return fig


def show(fig, key, height=330):
    st.plotly_chart(style(fig, height), width='stretch', key=key,
                    config={'displaylogo': False, 'responsive': True})


def timeline(result, fields):
    frame = monthly_frame(result)
    fig = go.Figure()
    palette = [TEAL, '#8A477B', '#84734D']
    for i, (field, label) in enumerate(fields):
        fig.add_scatter(x=dates(result), y=frame[field], name=label, mode='lines',
            line=dict(color=palette[i % 3], width=2.5, dash='solid' if i == 0 else 'dash'),
            hovertemplate='%{x|%b %Y}<br>$%{y:,.2f}<extra>%{fullData.name}</extra>')
    fig.update_xaxes(type='date', nticks=6, tickformat='%b\n%Y')
    fig.update_yaxes(title='USD', tickprefix='$', tickformat='~s', rangemode='tozero')
    return fig


def cash_chart(result, include_debt=False):
    fields = [('ending_cash', 'Month-end cash')]
    if include_debt:
        fields.append(('ending_debt', 'Drawn debt'))
    fig = timeline(result, fields)
    fig.add_hline(y=float(result.assumptions.cash_floor), line_dash='dot', line_color='#943D34',
                  annotation_text='Cash floor', annotation_position='bottom right')
    month = result.summary.minimum_cash_month
    fig.add_scatter(x=[dates(result)[month]], y=[float(result.summary.minimum_cash)], mode='markers',
        marker=dict(size=8, color=TEAL, symbol='diamond'), name='Minimum cash',
        hovertemplate='%{x|%b %Y}<br>Minimum cash: $%{y:,.2f}<extra></extra>')
    return fig


def bridge_chart(result):
    rows = profit_bridge(result)
    fig = go.Figure(go.Waterfall(orientation='h', y=[name for name, _ in rows],
        x=[float(value) for _, value in rows], measure=['relative'] * (len(rows) - 1) + ['total'],
        increasing=dict(marker=dict(color=TEAL)), decreasing=dict(marker=dict(color='#943D34')),
        totals=dict(marker=dict(color=INK)), connector=dict(line=dict(color='#A5B4C0')),
        customdata=[money(value) for _, value in rows],
        hovertemplate='%{y}: %{customdata}<extra></extra>'))
    fig.update_layout(showlegend=False, hovermode='closest')
    fig.update_xaxes(title='USD', tickprefix='$', tickformat='~s')
    fig.update_yaxes(autorange='reversed', showgrid=False)
    return fig
