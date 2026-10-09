"""Owned markup styles and shared chart tokens; no private Streamlit selectors."""

import streamlit as st

INK = '#182C3E'
MUTED = '#526477'
TEAL = '#145B72'
POLICY_COLORS = {'Conservative': TEAL, 'Balanced': '#84734D', 'Aggressive': '#8A477B'}
BAND_COLORS = {'Low': '#145B72', 'Medium': '#84734D', 'High': '#8A477B'}
FONT = 'Source Sans, sans-serif'

STYLE = """
<style>
.workbench-status{display:inline-flex;align-items:center;gap:.4rem;padding:.3rem .6rem;
 border-radius:.4rem;font-size:.875rem;font-weight:600;line-height:1.35;background:#EDF2F6;color:#344C60}
.workbench-status.good{background:#EAF5EF;color:#1F634B}
.workbench-status.warn{background:#FFF3DF;color:#805016}
.workbench-status.bad{background:#FFF0EE;color:#943D34}
.policy-comparison{container-type:inline-size}
.policy-table{width:100%;table-layout:fixed;border-collapse:collapse;font-size:1rem;background:white}
.policy-table caption{text-align:left;color:#526477;padding:0 0 .75rem}
.policy-table th,.policy-table td{padding:.75rem 1rem;border-bottom:1px solid #DCE4EB;text-align:right;vertical-align:top}
.policy-table th:first-child,.policy-table td:first-child{text-align:left}
.policy-table thead th{background:#EDF2F6;font-weight:600}
.policy-table td{font-variant-numeric:tabular-nums}
.policy-table .markers{display:block;font-size:.875rem;font-weight:400;color:#145B72;margin-top:.3rem}
.policy-mobile{display:none}
.policy-mobile article{background:white;border:1px solid #DCE4EB;border-radius:.5rem;padding:1rem}
.policy-mobile h3{font-size:1.2rem;margin:0 0 .5rem}
.policy-mobile dl{margin:.5rem 0 0}
.policy-mobile dl div{display:flex;justify-content:space-between;gap:1rem;padding:.45rem 0;border-bottom:1px solid #EDF2F6}
.policy-mobile dt{color:#526477}.policy-mobile dd{margin:0;text-align:right;font-variant-numeric:tabular-nums;font-weight:600}
@media(max-width:640px){.policy-table{display:none}.policy-mobile{display:grid;gap:1rem}}
@container(max-width:640px){.policy-table{display:none}.policy-mobile{display:grid;gap:1rem}}
@media(prefers-reduced-motion:reduce){.workbench-status{transition:none}}
</style>
"""


def apply_styles():
    st.html(STYLE)
