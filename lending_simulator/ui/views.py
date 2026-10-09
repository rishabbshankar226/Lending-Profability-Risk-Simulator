"""Only the selected analytical view is built on each rerun."""

from dataclasses import asdict, dataclass
from decimal import Decimal as D
from typing import Callable, Mapping

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lending_simulator.analytics import policy_population, query_text
from lending_simulator.decisions import Decision, select_strategy
from lending_simulator.data import Dataset
from lending_simulator.types import ModelResult
from lending_simulator.presentation import (monthly_frame, comparison_frame, cohort_heatmap,
    band_curves, assumption_register, evidence_register, month_label, limit_margins)
from lending_simulator.ui import charts
from lending_simulator.ui.components import caption, policy_summary, status_chip
from lending_simulator.ui.data import ScenarioSnapshot, compare_snapshots, stress_frame, applied_case_index
from lending_simulator.ui.formatting import money, percent, points, multiple, assumption_value
from lending_simulator.ui.state import FIELDS, DraftChange, draft_changes
from lending_simulator.ui.theme import POLICY_COLORS, BAND_COLORS


@dataclass(frozen=True)
class ViewContext:
    selected: ModelResult
    results: tuple[ModelResult, ...]
    dataset: Dataset
    decision: Decision
    actions: Mapping[str, Callable]


def secondary_metrics(items):
    for col, (label, value) in zip(st.columns(len(items)), items):
        with col:
            caption(label)
            st.markdown(f'**{value}**'.replace('$', r'\$'))


def render_overview(ctx):
    r, s = ctx.selected, ctx.selected.summary
    st.header('Overview')
    secondary_metrics((('Funded principal', money(s.funded_principal)),
                       ('Approval rate', percent(s.approval_rate)),
                       ('Contribution / funded loan', money(s.unit_contribution))))
    caption(f'First 24 months operating result: {money(s.operating_result_24m)} · Expected funded loans: {s.funded_loans:,.1f}. Contribution excludes platform expense.')
    cash, loss = limit_margins(r)
    if cash < 0 or (loss is not None and loss < 0) or not r.checks.passed:
        with st.container(horizontal=True, wrap=True):
            if cash < 0:
                st.button('Inspect cash shortfall', key='inspect_cash', on_click=ctx.actions['navigate'], args=('Funding & stress',))
            if loss is not None and loss < 0:
                st.button('Inspect credit assumptions', key='inspect_credit', on_click=ctx.actions['credit'])
            if not r.checks.passed:
                st.button('Inspect financial checks', key='inspect_checks', on_click=ctx.actions['navigate'], args=('Methodology',))
    profit_col, cash_col = st.columns(2)
    with profit_col:
        st.subheader('Operating profit over time')
        fig = charts.timeline(r, [('cumulative_operating_result', 'Cumulative operating profit')])
        origins = r.manifest()['operating_horizon_months']
        if len(r.monthly) > origins:
            fig.add_shape(type='rect', x0=charts.dates(r)[origins], x1=charts.dates(r)[-1],
                y0=0, y1=1, yref='paper', fillcolor='#EDF2F6', opacity=.6, line_width=0, layer='below')
            fig.add_annotation(x=charts.dates(r)[origins], y=1, yref='paper', text='Runoff', showarrow=False, xanchor='left')
        charts.show(fig, f'profit-{r.run_id}')
    with cash_col:
        st.subheader('Liquidity over time')
        charts.show(charts.cash_chart(r), f'cash-{r.run_id}')
    caption('Profit includes noncash charge-offs. Cash includes original loan advances, expected collections and debt movements. Charts use independent axes; compare policy margins in Policies.')
    with st.expander('How operating profit is calculated'):
        charts.show(charts.bridge_chart(r), f'bridge-{r.run_id}', 420)
        caption('Interest + merchant fees − funding, servicing, acquisition, net credit loss and platform expense. Principal advances and repayments are not revenue; net loss already includes recoveries.')
        from lending_simulator.ui.data import profit_bridge
        st.table(pd.DataFrame([(name, money(value)) for name, value in profit_bridge(r)], columns=['Component', 'USD']))
    with st.expander('Monthly values behind these charts'):
        st.dataframe(monthly_frame(r)[['period','operating_result','cumulative_operating_result','ending_cash']], hide_index=True, width='stretch')


def baseline_panel(ctx):
    with st.expander('Compare with a pinned scenario'):
        caption('Pin the applied scenario, then change assumptions. One baseline is held for this session; drafts and refreshes are not saved scenarios.')
        with st.container(horizontal=True, wrap=True):
            st.button('Pin applied scenario', key='pin_baseline', on_click=ctx.actions['pin'])
            if 'baseline' in st.session_state:
                st.button('Clear baseline', key='clear_baseline', on_click=ctx.actions['clear_baseline'])
        old = st.session_state.get('baseline')
        if old is None:
            st.info('No baseline pinned. Pin this applied scenario to compare your next run.')
            return
        current = ScenarioSnapshot.capture(ctx.results)
        comparison = compare_snapshots(old, current)
        caption('Baseline runs: '+', '.join(f'{r.policy.title()} {r.run_id}' for r in old.results))
        caption('Current runs: '+', '.join(f'{r.policy.title()} {r.run_id}' for r in current.results))
        if not comparison.compatible:
            st.warning(comparison.reason)
            return
        old_decision, new_decision = select_strategy(old.results), ctx.decision
        st.markdown(f'**Recommendation:** {(old_decision.recommended_policy or "None").title()} → {(new_decision.recommended_policy or "None").title()}')
        before, after = old.results[0].assumptions, current.results[0].assumptions
        changes = tuple(DraftChange(field, label, getattr(before, field), getattr(after, field))
                        for field, _, label, _ in FIELDS if getattr(before, field) != getattr(after, field))
        if changes:
            st.table(pd.DataFrame([{'Changed assumption': c.label,
                'Baseline': assumption_value(c.field,c.before),
                'Current': assumption_value(c.field,c.after)} for c in changes]))
        else:
            caption('Both applied scenarios use the same assumptions.')
        if not comparison.same_horizon:
            st.info(f'Runoff differs: baseline {comparison.baseline_months} months, current {comparison.current_months} months. Compare the common first 24 months below; full-runoff totals include different lengths of platform expense.')
            st.table(pd.DataFrame([{'Policy': before.policy.title(),
                f'Baseline profit ({len(before.monthly)}m)': money(before.summary.operating_result),
                f'Current profit ({len(after.monthly)}m)': money(after.summary.operating_result)}
                for before in old.results
                for after in current.results if after.policy == before.policy]))
        rows = []
        for d in comparison.deltas:
            rows.append({'Policy': d.policy.title(),
                'Change in profit' if comparison.same_horizon else 'Change in first-24-month profit': money(d.profit if comparison.same_horizon else d.profit_24m),
                'Change in minimum cash': money(d.cash), 'Change in equity gap': money(d.equity_gap),
                'Change in net loss': points(d.loss_pp), 'Change in approval rate': points(d.approval_pp)})
        st.table(pd.DataFrame(rows))
        caption('Same policy compared to itself. Parentheses / minus signs denote decreases. Higher cash and a smaller equity gap describe liquidity; starting equity has no modeled cost of equity. Multiple changed assumptions do not establish individual causal effects.')


def render_policies(ctx):
    st.header('Policies')
    policy_summary(ctx.results, ctx.decision.recommended_policy, ctx.selected.policy)
    for col, r in zip(st.columns(3), ctx.results):
        with col:
            st.button(f'View {r.policy.title()}', key=f'view_{r.policy}', width='stretch', on_click=ctx.actions['view'], args=(r.policy,))
    data = comparison_frame(ctx.results)
    profit, liquidity = st.columns(2)
    for col, title, values, key in (
        (profit, 'Full-runoff operating profit', [float(r.summary.operating_result) for r in ctx.results], 'policy-profit'),
        (liquidity, 'Cash margin to the selected floor', [float(limit_margins(r)[0]) for r in ctx.results], 'policy-cash')):
        with col:
            st.subheader(title)
            fig = go.Figure(go.Bar(x=[r.policy.title() for r in ctx.results], y=values,
                marker_color=[POLICY_COLORS[r.policy.title()] for r in ctx.results],
                hovertemplate='%{x}<br>$%{y:,.2f}<extra></extra>'))
            fig.update_yaxes(title='USD', tickprefix='$', tickformat='~s', rangemode='tozero')
            fig.add_hline(y=0, line_color='#8799A8')
            charts.show(fig, key)
    caption('Conservative approves low risk; Balanced adds medium; Aggressive adds high. Financial eligibility and profitability are separate. Equity changes liquidity feasibility, not modeled profit.')
    baseline_panel(ctx)
    with st.expander('Detailed policy economics and run identities'):
        st.dataframe(data, hide_index=True, width='stretch', column_config={
            'Approval rate': st.column_config.NumberColumn(format='percent'),
            'Net principal loss ratio': st.column_config.NumberColumn(format='percent')})


@st.cache_data(max_entries=6, show_spinner=False)
def cohort_scale(run_ids, _results):
    values = [cohort_heatmap(r).max().max() for r in _results]
    maximum = max((value for value in values if pd.notna(value)), default=0)
    return max(.001, float(maximum))


def render_cohorts(ctx):
    st.header('Cohorts')
    st.session_state.setdefault('cohort_cutoff', st.session_state.get('cohort_view', 'First 24 months'))
    cutoff = st.radio('Cohort cutoff', ['First 24 months', 'Complete runoff'], horizontal=True,
                       key='cohort_cutoff', on_change=ctx.actions['cohort'])
    heatmap = cohort_heatmap(ctx.selected, 23 if cutoff == 'First 24 months' else None)
    caption('Projected cumulative net principal loss, by origination month and loan age. Blank means unavailable, not zero; recoveries can reduce net loss.')
    if not heatmap.notna().any().any():
        st.info('No funded cohorts under this policy. Cohort loss ratios are unavailable.')
    else:
        fig = go.Figure(go.Heatmap(z=heatmap.values*100, x=list(heatmap.columns),
            y=[month_label(m) for m in heatmap.index], colorscale='Blues', zmin=0,
            zmax=cohort_scale(tuple(r.run_id for r in ctx.results), ctx.results)*100,
            colorbar=dict(title='Net loss %'), hoverongaps=False,
            hovertemplate='Origination: %{y}<br>Loan age: %{x} months<br>Projected net loss: %{z:.2f}%<extra></extra>'))
        fig.update_xaxes(title='Loan age (months)', nticks=8)
        fig.update_yaxes(autorange='reversed', title='Origination month', nticks=12)
        charts.show(fig, f'cohorts-{ctx.selected.run_id}-{cutoff}', 480)
        caption('Scale is shared across all applied policies and both cutoffs. Denominator: each cohort’s original funded principal; future ages at the selected cutoff remain blank.')
    curves = band_curves(ctx.selected)
    if curves.empty:
        st.info('No funded risk bands; repayment and net-loss ratios are unavailable.')
    else:
        st.subheader('Risk-band repayment and net loss')
        for col, field, title, bound in zip(st.columns(2),
            ['principal_repaid_ratio','net_loss_ratio'], ['Principal repaid / originated','Net loss / originated'], [True,False]):
            with col:
                fig = go.Figure()
                for band, group in curves.groupby('risk_band', sort=False):
                    fig.add_scatter(x=group.age, y=group[field], name=band, mode='lines',
                        line=dict(color=BAND_COLORS[band], width=2.5,
                                  dash={'Low':'solid','Medium':'dash','High':'dot'}[band]),
                        hovertemplate='Age %{x} months<br>%{y:.2%}<extra>%{fullData.name}</extra>')
                fig.update_xaxes(title='Loan age (months)', nticks=7)
                fig.update_yaxes(title=title, tickformat='.0%', range=[0,1] if bound else None, rangemode='tozero')
                charts.show(fig, f'band-{field}-{ctx.selected.run_id}', 320)
    with st.expander('Accessible projected cohort and risk-band values'):
        display = heatmap.copy()
        display.index = [month_label(m) for m in display.index]
        st.dataframe(display, width='stretch')
        if not curves.empty:
            st.table(curves.groupby('risk_band', sort=False).last()[['principal_repaid_ratio','net_loss_ratio']].map(percent))
            st.dataframe(curves, hide_index=True, width='stretch')


def stress_panel(ctx):
    st.subheader('Default and funding stress')
    caption('20 selected-policy cases: absolute lifetime-PD multipliers and annual funding rates. Other applied inputs stay fixed; these cases do not rank all three policies.')
    st.button('Run stress grid', key='run_stress', on_click=ctx.actions['stress'])
    saved = st.session_state.get('stress_points')
    if not saved or saved['run_id'] != ctx.selected.run_id:
        st.info('Stress grid has not been run for this applied policy. Run it when you want to explore the cases.')
        return
    frame = stress_frame(saved['points'])
    metrics = {'Operating profit':'operating_result','Minimum cash':'minimum_cash',
               'Net principal loss':'loss_ratio','Equity for cash floor':'additional_equity_required'}
    st.session_state.setdefault('stress_metric', st.session_state.get('stress_metric_view','Operating profit'))
    metric = st.selectbox('Stress result', list(metrics), key='stress_metric', on_change=ctx.actions['stress_metric'])
    field = metrics[metric]
    grid = frame.pivot(index='default_stress', columns='funding_rate', values=field)
    if grid.isna().all().all():
        st.info('Net loss is unavailable: no principal was funded. Costs, cash, and failure reasons remain available.')
    else:
        def cell(value):
            if pd.isna(value): return 'Unavailable'
            if field == 'loss_ratio': return f'{value:.2%}'
            return f'{"−" if value<0 else ""}${abs(value)/1000:,.0f}k' if abs(value)>=1000 else money(value)
        details = {(p['default_stress'],p['funding_rate']):p for p in frame.to_dict('records')}
        hover = [[f'{multiple(D(str(i)))} defaults · {percent(j)} funding<br>{metric}: '+
            (percent(grid.loc[i,j]) if field=='loss_ratio' else money(grid.loc[i,j]))+
            '<br>'+details[(i,j)]['profitability']+' · '+('Limits met' if details[(i,j)]['eligible'] else 'Limits failed')+
            '<br>'+details[(i,j)]['reasons'] for j in grid.columns] for i in grid.index]
        fig = go.Figure(go.Heatmap(z=grid.values, x=[percent(j) for j in grid.columns],
            y=[multiple(D(str(i))) for i in grid.index], text=[[cell(grid.loc[i,j]) for j in grid.columns] for i in grid.index],
            texttemplate='%{text}', customdata=hover, hovertemplate='%{customdata}<extra></extra>',
            colorscale='Blues' if field=='loss_ratio' else 'Reds' if field=='additional_equity_required' else 'RdBu',
            zmid=float(ctx.selected.assumptions.cash_floor) if field=='minimum_cash' else 0 if field=='operating_result' else None,
            colorbar=dict(title='Net loss ratio' if field=='loss_ratio' else 'USD', tickformat='.0%' if field=='loss_ratio' else '~s')))
        a = ctx.selected.assumptions
        present = applied_case_index(saved['points'], a) is not None
        if present:
            fig.add_scatter(x=[percent(a.funding_rate)], y=[multiple(a.default_stress)], mode='markers',
                marker=dict(symbol='square-open',size=35,color='#182C3E',line=dict(width=2)),
                showlegend=False, hoverinfo='skip')
        fig.update_xaxes(title='Annual funding rate')
        fig.update_yaxes(title='Lifetime PD multiplier')
        charts.show(fig, f'stress-{ctx.selected.run_id}-{field}', 380)
        caption('USD abbreviated in cells; full values and two distinct statuses appear in case detail. '+
                ('Outlined cell is the applied point.' if present else 'The exact applied stress/rate pair is outside this grid.'))
    current_index = applied_case_index(saved['points'], ctx.selected.assumptions)
    if current_index is None:
        current_index = 0
    st.session_state.setdefault('stress_case', st.session_state.get('stress_case_view',current_index))
    case = st.selectbox('Inspect a stress case', list(range(len(saved['points']))), key='stress_case',
        format_func=lambda i: f'{multiple(D(saved["points"][i]["default_stress"]))} defaults · {percent(D(saved["points"][i]["funding_rate"]))} annual funding',
        on_change=ctx.actions['stress_case'])
    point = saved['points'][case]
    pnl = D(point['operating_result'])
    limits = 'Meets limits' if point['eligible'] else 'Limits failed'
    status_chip(f'{limits} · '+('Profitable' if pnl>0 else 'Loss-making' if pnl<0 else 'Breakeven'), 'good' if point['eligible'] and pnl>0 else 'warn')
    caption(f'Profit {money(pnl)} · Minimum cash {money(D(point["minimum_cash"]))} · Net loss '+
        (percent(None) if point['loss_ratio']=='None' else percent(D(point['loss_ratio'])))+
        f' · Equity gap {money(D(point["additional_equity_required"]))}.')
    if point['reasons']: caption(point['reasons'])
    dirty = bool(draft_changes(st.session_state.draft_controls,ctx.selected.assumptions))
    st.button('Stage case as draft', key='stage_stress', disabled=dirty, on_click=ctx.actions['stage'])
    caption('Apply or restore unapplied changes before staging.' if dirty else 'Staging changes inputs only. Run scenario then compares all policies on those assumptions.')
    with st.expander('All stress case values and reasons'):
        st.dataframe(frame, hide_index=True, width='stretch')


def render_funding(ctx):
    st.header('Funding & stress')
    s = ctx.selected.summary
    charts.show(charts.cash_chart(ctx.selected,include_debt=True),f'funding-{ctx.selected.run_id}',360)
    secondary_metrics((('Equity for cash floor',money(s.additional_equity_required)),
                       ('Peak drawn debt',money(s.peak_debt)),('Minimum facility headroom',money(s.minimum_facility_headroom))))
    caption('Negative cash is an unfunded diagnostic path. Extra equity is not injected automatically and has no modeled cost of equity. Debt is limited by both collateral and facility capacity; defaults can require repayments.')
    stress_panel(ctx)
    with st.expander('Monthly funding and cash detail'):
        st.dataframe(monthly_frame(ctx.selected)[['period','ending_principal','ending_debt','net_debt_draw','funding_expense','ending_cash']],hide_index=True,width='stretch')


def render_methodology(ctx):
    st.header('Methodology')
    status_chip('Financial reconciliations passed' if ctx.selected.checks.passed else 'Financial reconciliation failed', 'good' if ctx.selected.checks.passed else 'bad')
    caption('Reconciled computations do not establish borrower prediction accuracy or real underwriting performance.')
    with st.expander('Model scope and financial timing',expanded=True):
        st.markdown('Loans originate at month-end. From the next month, defaults occur before scheduled payments; survivors repay principal and interest. Recoveries arrive after their selected lag. Debt adjusts to ending collateral; funding expense uses opening debt.')
        st.markdown('Principal repayments reduce the loan asset. A charge-off removes principal and future collections without creating another cash outflow. Net credit expense equals charge-offs less received recoveries; platform costs continue throughout runoff.')
        caption('Simplified management accounting; no taxes, prepayment, delinquency stages, price response, intramonth liquidity, rejected-applicant outcomes, or GAAP allowance/provision model.')
    with st.expander('Metric definitions'):
        st.table(pd.DataFrame([
            ('Operating profit','Revenue less credit loss, funding, servicing, acquisition and platform costs. Full runoff differs from the first 24 months.'),
            ('Cash margin','Minimum month-end cash less the selected floor; a negative margin is a shortfall.'),
            ('Equity requirement','Additional starting cash needed for the floor. No commitment or modeled cost of equity.'),
            ('Net principal loss','Charge-offs less received recoveries / original funded principal, through runoff.'),
            ('Lifetime PD','Illustrative 12-month default probability, multiplied by stress and capped at 100%.'),
            ('Contribution / loan','Full-runoff contribution before platform costs / expected funded loans.'),
            ('Expected counts','Demand-weighted loan/application counts; they can be fractional.')],columns=['Metric','Definition']))
    with st.expander('Financial reconciliation detail'):
        st.table(pd.DataFrame([(key.replace('_',' ').title(),str(value)) for key,value in asdict(ctx.selected.checks).items()],columns=['Check','Result']))
    with st.expander('Applied assumptions and effective default probabilities'):
        st.dataframe(pd.DataFrame(assumption_register(ctx.selected.assumptions)),hide_index=True,width='stretch')
        a=ctx.selected.assumptions
        caption('Applied effective lifetime PD: '+', '.join(f'{band.title()} {percent(a.lifetime_pd(band))}' for band in ('low','medium','high'))+'.')
    with st.expander('Historical evidence and source fitness'):
        evidence=evidence_register()
        st.warning(evidence['decision'])
        for source in evidence['sources']:
            st.markdown(f'[{source["publisher"]}]({source["url"]}) — {source["suitability"]}')
        caption('No historical default forecast, held-out evaluation, or borrower-level calibration. Annualized loss and longer-term cumulative loss cannot be substituted for 12-month PD.')
    with st.expander('Dataset, SQL, and applied run manifest'):
        st.json(ctx.dataset.manifest())
        st.dataframe(pd.DataFrame(policy_population(ctx.dataset)),hide_index=True,width='stretch')
        caption('SQL counts describe the unweighted base dataset; scenario counts include explicit growth weights.')
        st.code(query_text('policy_population'),language='sql')
        st.code(query_text('cohort_inputs'),language='sql')
        st.json(ctx.selected.manifest())


def render(view,ctx):
    {'Overview':render_overview,'Policies':render_policies,'Cohorts':render_cohorts,
     'Funding & stress':render_funding,'Methodology':render_methodology}[view](ctx)
