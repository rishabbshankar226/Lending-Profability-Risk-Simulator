"""Runtime Excel download using the XlsxWriter stack in the approved plan.

The workbook is a saved scenario plus small independent formula benchmarks.
It does not recalculate the whole portfolio when someone edits an input cell.
The same inspectable workbook specification supports the authoring QA renderer.
"""

from dataclasses import asdict, fields
from decimal import Decimal
from io import BytesIO

import xlsxwriter

from lending_simulator.presentation import RATE_INPUTS, units_for, workbook_payload
from lending_simulator.types import MonthlyResult, CohortMonth

ACCOUNTING = '$#,##0.00;($#,##0.00);"-"'
NUMBER = '#,##0.00;(#,##0.00);"-"'


def _number(value):
    if value is None:
        return "n.a."
    if isinstance(value, (Decimal, float, int)) and not isinstance(value, bool):
        return float(value)
    return value


def _sheet(name, rows, widths=None, formats=None, formulas=None, freeze=0):
    return {"name": name, "rows": rows, "widths": widths or {}, "formats": formats or {},
            "formulas": formulas or [], "freeze": freeze}


def workbook_spec(result, results, dataset) -> dict:
    payload = workbook_payload(result, results, dataset)
    s = result.summary
    summary_rows = [
        ["Lending scenario (USD)", None], ["Selected policy", result.policy.title()],
        ["Basis", "Synthetic expected-value projection, uncalibrated"],
        ["Operating result: first 24 months", _number(s.operating_result_24m)],
        ["Operating result: full runoff", _number(s.operating_result)],
        ["Contribution: full runoff", _number(s.contribution)],
        ["Lowest month-end cash", _number(s.minimum_cash)],
        ["Net loss / original funded principal", _number(s.loss_ratio)],
        ["Additional equity to meet cash floor", _number(s.additional_equity_required)],
        ["Expected funded loans", _number(s.funded_loans)],
        ["Funded principal", _number(s.funded_principal)],
        ["Contribution / funded loan", _number(s.unit_contribution)],
        [], ["Workbook behavior", "Saved portfolio outputs; rerun the app to refresh. Benchmark cells recalculate independently."],
    ]
    assumption_rows = [
        ["Run manifest", "Selected scenario"], ["Run ID", result.run_id],
        ["Policy", result.policy], ["Dataset hash", dataset.dataset_hash],
        ["Model version", result.manifest()["model_version"]],
        ["Full-runoff months", len(result.monthly)], ["Currency", "USD"],
        ["Evidence", "Contextual comparison only; no historical calibration"], [],
        list(payload["assumptions"][0]),
    ]
    for row in payload["assumptions"]:
        name = row["Assumption"]
        assumption_rows.append([name, _number(getattr(result.assumptions, name)), row["Unit"], row["Classification"],
                                row["Timing / definition"], row["Source"], row["Source date"]])
    monthly_fields = [f.name for f in fields(MonthlyResult)]
    monthly_rows = [monthly_fields, [units_for(n) for n in monthly_fields]]
    monthly_rows += [[_number(getattr(row, n)) for n in monthly_fields] for row in result.monthly]
    cohort_fields = [f.name for f in fields(CohortMonth)]
    cohort_rows = [cohort_fields, [units_for(n) for n in cohort_fields]]
    cohort_rows += [[_number(getattr(row, n)) for n in cohort_fields] for row in result.cohorts]
    comparison = payload["comparison"]
    policy_rows = [list(comparison[0])] + [list(row.values()) for row in comparison]

    # An independently computed float oracle supplies cached preview values.
    # Formula cells remain live and are recalculated during authoring QA.
    loan_rows = [
        ["Independent amortization benchmark"], [], ["Original principal", 1200.0],
        ["Annual nominal interest rate", .12], ["Payments", 12],
        ["Monthly interest rate", None], [], ["Monthly payment", None],
        ["Edit the blue inputs. This isolated benchmark is not the portfolio forecast."], [],
        ["Payment month", "Opening principal", "Payment", "Interest", "Principal paid", "Ending principal"],
    ]
    rate, principal, term = .12 / 12, 1200., 12
    payment = principal * rate / (1 - (1 + rate) ** -term)
    loan_formulas = [
        {"cell": "B6", "formula": "=B4/12", "cached": rate},
        {"cell": "B8", "formula": "=IF(B6=0,B3/B5,B3*B6/(1-(1+B6)^(-B5)))", "cached": payment},
    ]
    for age in range(1, 13):
        excel_row = age + 11
        interest = principal * rate
        paid = principal if age == 12 else min(principal, payment - interest)
        actual_payment = interest + paid
        ending = principal - paid
        loan_rows.append([age, None, None, None, None, None])
        loan_formulas += [
            {"cell": f"B{excel_row}", "formula": "=$B$3" if age == 1 else f"=F{excel_row - 1}", "cached": principal},
            {"cell": f"C{excel_row}", "formula": f"=IF(A{excel_row}=$B$5,B{excel_row}+D{excel_row},$B$8)", "cached": actual_payment},
            {"cell": f"D{excel_row}", "formula": f"=B{excel_row}*$B$6", "cached": interest},
            {"cell": f"E{excel_row}", "formula": f"=MIN(B{excel_row},C{excel_row}-D{excel_row})", "cached": paid},
            {"cell": f"F{excel_row}", "formula": f"=B{excel_row}-E{excel_row}", "cached": ending},
        ]
        principal = ending
    loan_rows += [[], ["Total interest", None], ["Total principal paid", None]]
    loan_formulas += [
        {"cell": "B25", "formula": "=SUM(D12:D23)", "cached": payment * 12 - 1200},
        {"cell": "B26", "formula": "=SUM(E12:E23)", "cached": 1200},
    ]
    default_rows = [
        ["Independent default and recovery benchmark"], [], ["Principal at origination", 900.],
        ["Default month", 1], ["Recovery fraction", .25], ["Recovery lag (months)", 3],
        ["Full-runoff net principal loss", None],
        ["Charge-off reduces the asset; the original advance was the cash outflow."], [], [],
        ["Month", "Opening principal", "Originations", "Charge-offs", "Recoveries", "Ending principal", "Net loss"],
    ]
    default_formulas = [{"cell": "B7", "formula": "=B3*(1-B5)", "cached": 675}]
    for month in range(5):
        r = month + 12
        opening = 900 if month == 1 else 0
        orig = 900 if month == 0 else 0
        charge = 900 if month == 1 else 0
        recovery = 225 if month == 4 else 0
        ending = opening + orig - charge
        default_rows.append([month, None, None, None, None, None, None])
        default_formulas += [
            {"cell": f"B{r}", "formula": "=0" if month == 0 else f"=F{r - 1}", "cached": opening},
            {"cell": f"C{r}", "formula": f"=IF(A{r}=0,$B$3,0)", "cached": orig},
            {"cell": f"D{r}", "formula": f"=IF(A{r}=$B$4,B{r},0)", "cached": charge},
            {"cell": f"E{r}", "formula": f"=IF(A{r}=$B$4+$B$6,$B$3*$B$5,0)", "cached": recovery},
            {"cell": f"F{r}", "formula": f"=B{r}+C{r}-D{r}", "cached": ending},
            {"cell": f"G{r}", "formula": f"=D{r}-E{r}", "cached": charge - recovery},
        ]

    check_rows = [["Financial reconciliation (USD)", "Maximum absolute difference", "Internal tolerance"],
                  ["Loan roll-forward", float(result.checks.loan_residual), float(result.checks.tolerance)],
                  ["Debt roll-forward", float(result.checks.debt_residual), float(result.checks.tolerance)],
                  ["Cash roll-forward", float(result.checks.cash_residual), float(result.checks.tolerance)],
                  ["Simplified equity identity", float(result.checks.equity_residual), float(result.checks.tolerance)],
                  ["Cohort / portfolio", float(result.checks.cohort_residual), float(result.checks.tolerance)],
                  ["Full runoff / recoveries", float(result.checks.runoff_residual), float(result.checks.tolerance)],
                  [], ["These saved checks refer to the manifest's run. They do not validate edits to snapshots."]]
    sources = [["Historical evidence", "URL", "Use / limitation"]]
    sources += [[x["publisher"], x["url"], x["suitability"]] for x in payload["sources"]["sources"]]
    return {"selected_run_id": result.run_id, "sheets": [
        _sheet("Summary", summary_rows, {0: 44, 1: 95}, {"B4:B7": ACCOUNTING, "B8": "0.00%", "B9:B12": NUMBER}),
        _sheet("Assumptions", assumption_rows, {0: 24, 1: 70, 2: 36, 3: 16, 4: 76, 5: 27, 6: 15}, freeze=10),
        _sheet("Policies", policy_rows, {0: 18, 11: 56, 12: 20},
               {"B2:B4": "0.00%", "H2:H4": "0.00%", "D2:G4": ACCOUNTING, "I2:J4": ACCOUNTING}, freeze=1),
        _sheet("Monthly snapshot", monthly_rows, formats={"B3:AA100": NUMBER}, freeze=2),
        _sheet("Cohort snapshot", cohort_rows, formats={"E3:P2000": NUMBER}, freeze=2),
        _sheet("Loan benchmark", loan_rows, {0: 24, 1: 23, 2: 20, 3: 20, 4: 22, 5: 24},
               {"B3": ACCOUNTING, "B4": "0.0%", "B6": "0.0%", "B8": ACCOUNTING, "B12:F23": ACCOUNTING, "B25:B26": ACCOUNTING}, loan_formulas),
        _sheet("Default benchmark", default_rows, {0: 27, 1: 23, 2: 20, 3: 20, 4: 20, 5: 22, 6: 20},
               {"B3": ACCOUNTING, "B5": "0.0%", "B7": ACCOUNTING, "B12:G16": ACCOUNTING}, default_formulas),
        _sheet("Checks", check_rows, {0: 75, 1: 28, 2: 28}, {"B2:B7": "0.00", "C2:C7": "0.00E+00"}),
        _sheet("Sources", sources, {0: 38, 1: 115, 2: 110}),
    ]}


def scenario_workbook(result, results, dataset) -> bytes:
    spec = workbook_spec(result, results, dataset)
    output = BytesIO()
    with xlsxwriter.Workbook(output, {"in_memory": True, "strings_to_formulas": False, "strings_to_urls": False}) as book:
        normal = book.add_format({"font_name": "Arial", "font_size": 10, "valign": "vcenter"})
        header = book.add_format({"font_name": "Arial", "font_size": 10, "bold": True, "bg_color": "#243e54", "font_color": "white", "text_wrap": True, "valign": "vcenter"})
        formula = book.add_format({"font_name": "Arial", "font_size": 10, "num_format": ACCOUNTING})
        editable = book.add_format({"font_name": "Arial", "font_size": 10, "font_color": "#1d4ed8", "bg_color": "#fff4cc", "num_format": NUMBER})
        for sheet in spec["sheets"]:
            ws = book.add_worksheet(sheet["name"])
            ws.hide_gridlines(2)
            width = max(len(row) for row in sheet["rows"])
            ws.set_column(0, width - 1, 25, normal)
            for col, col_width in sheet["widths"].items():
                ws.set_column(col, col, col_width, normal)
            for i, row in enumerate(sheet["rows"]):
                ws.write_row(i, 0, row, normal)
            if sheet["name"] not in ("Summary", "Loan benchmark", "Default benchmark"):
                ws.set_row(0, 32, header)
                ws.write_row(0, 0, sheet["rows"][0], header)
            if sheet["freeze"]:
                ws.freeze_panes(sheet["freeze"], 1)
            for cell_range, number_format in sheet["formats"].items():
                fmt = book.add_format({"font_name": "Arial", "font_size": 10, "num_format": number_format})
                from xlsxwriter.utility import xl_cell_to_rowcol
                first, _, last = cell_range.partition(":")
                r1, c1 = xl_cell_to_rowcol(first)
                r2, c2 = xl_cell_to_rowcol(last or first)
                for r in range(r1, min(r2 + 1, len(sheet["rows"]))):
                    for c in range(c1, min(c2 + 1, len(sheet["rows"][r]))):
                        ws.write(r, c, sheet["rows"][r][c], fmt)
            for cell in sheet["formulas"]:
                cell_format = book.add_format({"font_name": "Arial", "font_size": 10, "num_format": "0.0%"}) if sheet["name"] == "Loan benchmark" and cell["cell"] == "B6" else formula
                ws.write_formula(cell["cell"], cell["formula"], cell_format, cell["cached"])
            if sheet["name"] in ("Loan benchmark", "Default benchmark"):
                for r in ([3, 4] if sheet["name"] == "Loan benchmark" else [3, 5, 6]):
                    val = sheet["rows"][r - 1][1]
                    is_rate = r == (4 if sheet["name"] == "Loan benchmark" else 5)
                    input_format = book.add_format({"font_name": "Arial", "font_size": 10, "font_color": "#1d4ed8", "bg_color": "#fff4cc", "num_format": "0.0%" if is_rate else NUMBER})
                    ws.write(r - 1, 1, val, input_format)
                if sheet["name"] == "Loan benchmark":
                    ws.data_validation("B3", {"validate": "decimal", "criteria": ">", "value": 0})
                    ws.data_validation("B4", {"validate": "decimal", "criteria": "between", "minimum": 0, "maximum": 1})
                    ws.data_validation("B5", {"validate": "integer", "criteria": "==", "value": 12})
                else:
                    ws.data_validation("B3", {"validate": "decimal", "criteria": ">", "value": 0})
                    ws.data_validation("B4", {"validate": "integer", "criteria": "==", "value": 1})
                    ws.data_validation("B5", {"validate": "decimal", "criteria": "between", "minimum": 0, "maximum": 1})
                    ws.data_validation("B6", {"validate": "integer", "criteria": "between", "minimum": 0, "maximum": 3})
                ws.set_row(10, 32)
                ws.write_row(10, 0, sheet["rows"][10], header)
                ws.set_column(7, 7, 95, normal)
                ws.write(1, 7, "Illustrative independent case. Edit blue inputs; formulas recalculate.", normal)
                # Keep longer explanations away from the benchmark table.
                ws.write(7 if sheet["name"] == "Default benchmark" else 8, 0, "", normal)
            if sheet["name"] in ("Monthly snapshot", "Cohort snapshot"):
                unit_format = book.add_format({"font_name": "Arial", "font_size": 10, "text_wrap": True, "valign": "vcenter"})
                ws.set_row(1, 44)
                ws.write_row(1, 0, sheet["rows"][1], unit_format)
            if sheet["name"] == "Checks":
                ws.conditional_format("B2:B7", {"type": "formula", "criteria": "=ABS(B2)>C2", "format": book.add_format({"font_color": "#9f2626", "bg_color": "#fee2e2"})})
            ws.set_landscape()
            ws.fit_to_pages(1, 0)
    return output.getvalue()
