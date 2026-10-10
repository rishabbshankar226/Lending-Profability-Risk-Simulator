"""Compact analytical components using native controls and semantic owned markup."""

from html import escape

import streamlit as st

from lending_simulator.decisions import evaluate_policy
from lending_simulator.presentation import limit_margins, month_label
from lending_simulator.ui.formatting import money, percent, points
from lending_simulator.ui.theme import MUTED


def caption(text):
    st.html(f'<p class="workbench-caption">{escape(text)}</p>')


def readable_table(frame):
    """Keep native table behavior with opaque, readable row/column headers."""
    st.table(frame.style.set_table_styles([
        {'selector': 'th', 'props': [('color', MUTED), ('font-weight', '600')]},
    ]))


def status(result):
    limits = evaluate_policy(result)
    profit = result.summary.operating_result
    profitability = 'Profitable' if profit > 0 else 'Loss-making' if profit < 0 else 'Breakeven'
    if not result.checks.passed:
        return 'Unreconciled diagnostic', 'bad'
    reason = 'Meets limits' if limits.eligible else '; '.join(limits.reasons)
    return f'{reason} · {profitability}', 'good' if limits.eligible and profit > 0 else 'warn'


def status_chip(text, tone='warn'):
    st.html(f'<span class="workbench-status {escape(tone)}">{escape(text)}</span>')


def decision_summary(result, decision, on_view_recommended):
    with st.container(border=True, key='decision_summary'):
        recommendation, viewing = st.columns([2, 1], vertical_alignment='center')
        with recommendation:
            if decision.recommended_policy:
                st.header(f'Recommended policy: {decision.recommended_policy.title()}')
                caption('Highest projected full-runoff profit within the cash and loss limits.')
            else:
                title = 'No eligible policy' if decision.status == 'no_eligible_policy' else 'No positive-profit recommendation'
                st.header(title)
                st.warning(decision.message)
            if decision.diagnostic_policy:
                caption(f'Diagnostic policy: {decision.diagnostic_policy.title()} · No positive-profit recommendation.')
        with viewing:
            st.markdown(f'**Viewing policy: {result.policy.title()}**')
            text, tone = status(result)
            status_chip(text, tone)
            if decision.recommended_policy and result.policy != decision.recommended_policy:
                st.button('View recommended', key='view_recommended', width='stretch',
                          on_click=on_view_recommended, args=(decision.recommended_policy,))
    a, s = result.assumptions, result.summary
    cash, loss = limit_margins(result)
    cols = st.columns(3)
    with cols[0]:
        st.metric('Operating result · full runoff', money(s.operating_result), border=True,
                  help='Interest + merchant fees, less credit losses, funding, servicing, acquisition and all platform costs.')
        caption(f'{len(result.monthly)} months through {month_label(len(result.monthly)-1)} · Includes repayment and recovery runoff.')
    with cols[1]:
        label = 'Cash cushion above floor' if cash > 0 else 'Cash shortfall to floor' if cash < 0 else 'Cash at floor'
        st.metric(label, money(cash.copy_abs()), border=True, help='Lowest month-end cash minus the selected cash floor.')
        caption(f'Minimum cash: {money(s.minimum_cash)} · Floor: {money(a.cash_floor)} · {month_label(s.minimum_cash_month)}.')
    with cols[2]:
        label = 'Loss headroom to cap' if loss is None or loss > 0 else 'Loss cap exceeded by' if loss < 0 else 'Loss at cap'
        st.metric(label, points(None if loss is None else loss.copy_abs()), border=True,
                  help='Net loss cap minus the full-runoff loss ratio, in percentage points; unavailable without funded principal.')
        caption(f'Net principal loss: {percent(s.loss_ratio)} · Cap: {percent(a.loss_cap)}.')
        if s.loss_ratio is None:
            caption('No funded loans · Net loss and credit headroom are unavailable.')
    caption('USD, rounded · pp = percentage points. Status uses unrounded values. Charts and downloads use the viewed applied policy.')


def policy_summary(results, recommended, viewed):
    """The same fields in a desktop table and narrow-screen definition lists."""
    fields = (
        ('Approval rate', lambda r: percent(r.summary.approval_rate)),
        ('Operating profit', lambda r: money(r.summary.operating_result)),
        ('Minimum cash', lambda r: money(r.summary.minimum_cash)),
        ('Net principal loss', lambda r: percent(r.summary.loss_ratio)),
        ('Equity for cash floor', lambda r: money(r.summary.additional_equity_required)),
        ('Limit / profit status', lambda r: status(r)[0]),
    )
    def marker(r):
        return ' · '.join(label for label, matches in (
            ('Recommended', r.policy == recommended), ('Viewing', r.policy == viewed)) if matches)

    header = ''.join(f'<th scope="col">{r.policy.title()}<span class="markers">{marker(r)}</span></th>' for r in results)
    rows = ''.join('<tr><th scope="row">'+escape(label)+'</th>'+''.join(
        '<td>'+escape(value(r))+'</td>' for r in results)+'</tr>' for label, value in fields)
    table = f'<table class="policy-table"><caption>Three policies on the same applied inputs. Profit and limit status are separate.</caption><thead><tr><th scope="col">Measure</th>{header}</tr></thead><tbody>{rows}</tbody></table>'
    cards = ''.join(f'<article aria-label="{r.policy.title()} policy"><h3>{r.policy.title()}</h3><p>{marker(r)}</p><dl>'+''.join(
        '<div><dt>'+escape(label)+'</dt><dd>'+escape(value(r))+'</dd></div>' for label, value in fields)+'</dl></article>' for r in results)
    st.html('<div class="policy-comparison">'+table+'<div class="policy-mobile">'+cards+'</div></div>')
