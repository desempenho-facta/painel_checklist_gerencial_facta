"""
Relatório individual da loja em PDF: situação do mês, aproveitamento por bloco,
pontos de melhoria (perguntas com Não), casos graves e histórico mês a mês.
"""

from __future__ import annotations

import io
from datetime import datetime
from xml.sax.saxutils import escape as esc

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import config as C
from . import regras as R
from .perguntas import PERGUNTAS_TEXTO
from .ui import PASTA_ASSETS

NAVY = colors.HexColor(C.COR_NAVY)
LARANJA = colors.HexColor(C.COR_LARANJA)
VERDE = colors.HexColor(C.COR_VERDE)
VERMELHO = colors.HexColor(C.COR_VERMELHO)
AMBAR = colors.HexColor(C.COR_AMBAR)
CINZA = colors.HexColor("#6b6b6b")

_est = getSampleStyleSheet()
TITULO = ParagraphStyle("t", parent=_est["Title"], fontName="Helvetica-Bold", fontSize=16, textColor=NAVY,
                        alignment=0, spaceAfter=2)
SUB = ParagraphStyle("s", parent=_est["Normal"], fontSize=9.5, textColor=CINZA, spaceAfter=8)
SECAO = ParagraphStyle("h", parent=_est["Heading2"], fontName="Helvetica-Bold", fontSize=12, textColor=NAVY,
                       spaceBefore=10, spaceAfter=4)
TEXTO = ParagraphStyle("p", parent=_est["Normal"], fontSize=9, leading=12)
PEQ = ParagraphStyle("pp", parent=TEXTO, fontSize=8, leading=10, textColor=CINZA)
CEL = ParagraphStyle("c", parent=TEXTO, fontSize=8.5, leading=11)
CELH = ParagraphStyle("ch", parent=TEXTO, fontSize=7.6, leading=9.5)
CARD_NUM = ParagraphStyle("cn", parent=TEXTO, fontName="Helvetica-Bold", fontSize=10.5, alignment=TA_CENTER, leading=12.5)
CARD_ROT = ParagraphStyle("cr", parent=TEXTO, fontSize=7.5, alignment=TA_CENTER, textColor=CINZA)


def _cor_score(v):
    if pd.isna(v):
        return CINZA
    return VERDE if v > C.MATURIDADE_DESENV_ATE else AMBAR if v > C.MATURIDADE_REATIVA_ATE else VERMELHO


def _barras_blocos(p: pd.Series, rede: dict | None) -> Drawing:
    larg, alt_linha = 170 * mm, 15
    blocos = list(C.BLOCOS)
    d = Drawing(larg, alt_linha * len(blocos) + 14)
    x0, xmax = 95, larg - 45
    for i, b in enumerate(blocos):
        y = d.height - (i + 1) * alt_linha
        v = float(p[f"pct_{b}"])
        d.add(String(0, y + 3, b, fontName="Helvetica", fontSize=8.5))
        d.add(Rect(x0, y + 1, xmax - x0, 9, fillColor=colors.HexColor("#eeeeee"), strokeColor=None))
        d.add(Rect(x0, y + 1, (xmax - x0) * v, 9, strokeColor=None,
                   fillColor=VERMELHO if v < C.LIMIAR_BLOCO else colors.HexColor(C.COR_AZUL)))
        d.add(String(xmax + 4, y + 3, f"{v * 100:.0f}%".replace(".", ","), fontName="Helvetica-Bold", fontSize=8.5))
        if rede and pd.notna(rede.get(b)):
            xr = x0 + (xmax - x0) * rede[b]
            d.add(Line(xr, y - 1, xr, y + 12, strokeColor=colors.black, strokeWidth=1.2))
    xl = x0 + (xmax - x0) * C.LIMIAR_BLOCO
    d.add(Line(xl, 2, xl, d.height - 2, strokeColor=CINZA, strokeDashArray=[2, 2], strokeWidth=0.6))
    d.add(String(x0, 0, "Linha pontilhada: 60% (bloco bom). Traço preto: média da rede no mês.",
                 fontName="Helvetica", fontSize=7, fillColor=CINZA))
    return d


def gerar_pdf(loja: str, p: pd.Series, historico: pd.DataFrame, grave: pd.Series | None,
              rede_blocos: dict | None, visao: str) -> bytes:
    """p: preenchimento usado no diagnóstico (linha de validos). historico: R.historico_loja."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=14 * mm,
                            bottomMargin=14 * mm, title=f"Diagnóstico {loja}", author="Monitoria & Desempenho Facta")
    h = []

    logo = PASTA_ASSETS / "facta_logo.png"
    cab = Table([[Image(str(logo), width=34 * mm, height=10 * mm),
                  Paragraph('<font color="white"><b>DIAGNÓSTICO DA LOJA</b></font>',
                            ParagraphStyle("x", parent=TEXTO, fontSize=13, alignment=2))]],
                colWidths=[60 * mm, 114 * mm])
    cab.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                             ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                             ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    h += [cab, Spacer(1, 6)]
    h.append(Paragraph(esc(loja), TITULO))
    h.append(Paragraph(
        f"Preenchimento de {p['timestamp']:%d/%m/%Y às %H:%M} ({R.rotulo_mes(p['competencia'])}) · coordenador "
        f"{esc(p['COORDENADOR'].title())} · supervisor {esc(p['SUPERVISOR'].title())} · gerado em "
        f"{datetime.now(C.FUSO):%d/%m/%Y %H:%M} ({esc(visao)})", SUB))

    def card(n, r, cor=colors.black):
        return [Paragraph(f'<font color="{cor.hexval().replace("0x", "#")}">{n}</font>', CARD_NUM), Paragraph(r, CARD_ROT)]

    cards = [card(f"{p['score']:.2f}".replace(".", ","), "Score (0 a 100)", _cor_score(p["score"])),
             card(p["maturidade"], "Maturidade"), card(p["risco"], "Nível de risco"),
             card(p["ciclo"], "Ciclo"), card(p["quadrante"], "Quadrante do treino"),
             card("Com chamados" if p["estrutura"] == "Com chamados abertos" else "Sem chamados", "Estrutura (Q36)")]
    t = Table([[c[0] for c in cards], [c[1] for c in cards]], colWidths=[29 * mm] * 6)
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                           ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e5e5")),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fafafa"))]))
    h.append(t)

    avisos = []
    if p["supervisao_especial"]:
        avisos.append(f"<b>Supervisão especial ({esc(p['tipo_especial'])}).</b> As respostas estão como foram gravadas, "
                      "mas a loja não entra no score nem na cobertura do coordenador neste mês.")
    if grave is not None:
        partes = ", ".join(f"{s} há {n} {'preenchimento' if n == 1 else 'preenchimentos seguidos'}"
                           for s, n in grave["por_sinal"].items())
        avisos.append(f"<b>Caso grave há {grave['preenchimentos_seguidos']} "
                      f"{'preenchimento' if grave['preenchimentos_seguidos'] == 1 else 'preenchimentos seguidos'} "
                      f"(desde {R.rotulo_mes(grave['desde'])}).</b> {partes}.")
    for a in avisos:
        h += [Spacer(1, 4), Paragraph(a, ParagraphStyle("av", parent=TEXTO, backColor=colors.HexColor("#fff1e8"),
                                                          borderPadding=5, leftIndent=2))]

    h.append(Paragraph("Aproveitamento por bloco", SECAO))
    h.append(_barras_blocos(p, rede_blocos))

    h.append(Paragraph("Pontos de melhoria", SECAO))
    linhas = []
    for bloco, b in C.BLOCOS.items():
        naos = [q for q in b["perguntas"] if p[q] == "Não"]
        if naos:
            perdeu = sum(C.PONTO_POR_SIM[q] for q in naos)
            perdeu_txt = f"{perdeu:.1f}".replace(".", ",")
            linhas.append([Paragraph(f"<b>{bloco}</b><br/><font size=7.5 color='#6b6b6b'>perdeu "
                                     f"{perdeu_txt} de {b['peso']} pontos</font>", CEL),
                           Paragraph("<br/>".join(f"<b>{q}</b> {PERGUNTAS_TEXTO[q]}" for q in naos), CEL)])
    if linhas:
        t = Table(linhas, colWidths=[38 * mm, 136 * mm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
                               ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        h.append(t)
    else:
        h.append(Paragraph("Nenhuma pergunta com Não neste preenchimento.", TEXTO))

    h.append(Paragraph("Histórico da loja", SECAO))
    cab_h = ["Mês", "Data", "Score", "Maturidade", "Risco", "Ciclo", "Estrutura", "Sup. esp."]
    dados_h = [cab_h] + [[R.rotulo_mes(r["competencia"]), f"{r['timestamp']:%d/%m/%y}",
                          f"{r['score']:.2f}".replace(".", ","), r["maturidade"], r["risco"], r["ciclo"],
                          "Com chamados" if r["estrutura"] == "Com chamados abertos" else "Sem chamados",
                          "Sim" if r["supervisao_especial"] else ""]
                         for _, r in historico.sort_values("competencia", ascending=False).iterrows()]
    t = Table([[Paragraph(esc(str(c)), CELH) for c in l] for l in dados_h],
              colWidths=[27 * mm, 19 * mm, 13 * mm, 27 * mm, 20 * mm, 32 * mm, 22 * mm, 14 * mm], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f4f4")]),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    # texto do cabeçalho em branco
    for j in range(len(cab_h)):
        t._cellvalues[0][j] = Paragraph(f'<font color="white"><b>{cab_h[j]}</b></font>', CELH)
    h.append(t)

    h.append(Paragraph("Respostas do preenchimento", SECAO))
    resp, spans = [], []
    for bloco, b in C.BLOCOS.items():
        spans.append(("SPAN", (0, len(resp)), (-1, len(resp))))
        resp.append([Paragraph(f'<font color="{C.COR_LARANJA}"><b>{bloco.upper()}</b></font>', CEL), "", ""])
        for q in b["perguntas"]:
            r = p[q] or "vazio"
            cor = C.COR_VERDE if r == "Sim" else C.COR_VERMELHO if r == "Não" else "#6b6b6b"
            resp.append([Paragraph(f"<b>{q}</b>", CEL), Paragraph(PERGUNTAS_TEXTO[q], CEL),
                         Paragraph(f'<font color="{cor}"><b>{r}</b></font>', CEL)])
    t = Table(resp, colWidths=[12 * mm, 146 * mm, 16 * mm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.2, colors.HexColor("#e2e2e2"))]
                          + spans))
    h.append(t)
    h += [Spacer(1, 8), Paragraph("Checklist Gerencial · Monitoria & Desempenho Facta", PEQ)]

    doc.build(h)
    return buf.getvalue()
