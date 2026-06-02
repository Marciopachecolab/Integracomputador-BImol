# -*- coding: utf-8 -*-
"""
Gera um PDF de exemplo do Mapa da Placa definitivo.

Cria dados sinteticos representativos de uma corrida ZDC BioManguinhos
(3 pocos por amostra, 32 amostras + controles) e renderiza diretamente
em PDF via reportlab, espelhando as decisoes de layout do exporter Excel.

Uso:
    python scripts/gerar_exemplo_mapa_placa.py
"""
from __future__ import annotations

import os
import random
import sys
from datetime import datetime
from pathlib import Path

# garante imports do projeto quando rodado fora do pytest
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

from domain.mapa_placa_layout import (
    CLASSIF_DETECTAVEL,
    CLASSIF_INDETERMINADO,
    CLASSIF_INVALIDO,
    CLASSIF_NAO_DETECTAVEL,
    AlvoCelula,
    BlocoAmostra,
    ControleQuadro,
    classificar_amostra,
    distribuir_alvos_grid,
    formatar_ct,
    montar_mapa,
)


def _ct(rng: random.Random, faixa=(18.0, 35.0)) -> float:
    return round(rng.uniform(*faixa), 2)


def _gerar_blocos_zdc(rng: random.Random, total: int):
    """Gera blocos sinteticos de ZDC com mistura realista de resultados."""
    blocos = []
    cenarios = [
        ("nd",),
        ("nd",),
        ("nd",),
        ("nd",),
        ("det_den1",),
        ("det_den2",),
        ("det_zk",),
        ("det_chik",),
        ("ind",),
        ("det_multi",),
    ]
    for i in range(total):
        codigo = str(263499000 + rng.randint(100, 999))
        cenario = rng.choice(cenarios)[0]
        # CTs por alvo
        ct_zk = ""
        ct_chik = ""
        ct_den1 = ""
        ct_den2 = ""
        ct_den3 = ""
        ct_den4 = ""
        res = {
            "ZK": "Nao Detectavel",
            "CHIK": "Nao Detectavel",
            "DEN1": "Nao Detectavel",
            "DEN2": "Nao Detectavel",
            "DEN3": "Nao Detectavel",
            "DEN4": "Nao Detectavel",
        }
        if cenario == "det_den1":
            ct_den1 = _ct(rng, (25.0, 32.0))
            res["DEN1"] = "Detectavel"
        elif cenario == "det_den2":
            ct_den2 = _ct(rng, (25.0, 32.0))
            res["DEN2"] = "Detectavel"
        elif cenario == "det_zk":
            ct_zk = _ct(rng, (25.0, 32.0))
            res["ZK"] = "Detectavel"
        elif cenario == "det_chik":
            ct_chik = _ct(rng, (25.0, 32.0))
            res["CHIK"] = "Detectavel"
        elif cenario == "det_multi":
            ct_den1 = _ct(rng, (25.0, 32.0))
            ct_den2 = _ct(rng, (25.0, 32.0))
            res["DEN1"] = "Detectavel"
            res["DEN2"] = "Detectavel"
        elif cenario == "ind":
            ct_den3 = _ct(rng, (36.5, 39.0))
            res["DEN3"] = "Indeterminado"

        ct_rp1 = _ct(rng, (24.0, 30.0))
        ct_rp2 = _ct(rng, (24.0, 30.0))
        ct_rp3 = _ct(rng, (24.0, 30.0))

        alvos_celulas = [
            AlvoCelula("ZK", formatar_ct(ct_zk)),
            AlvoCelula("CHIK", formatar_ct(ct_chik)),
            AlvoCelula("DEN1", formatar_ct(ct_den1)),
            AlvoCelula("DEN2", formatar_ct(ct_den2)),
            AlvoCelula("DEN3", formatar_ct(ct_den3)),
            AlvoCelula("DEN4", formatar_ct(ct_den4)),
            AlvoCelula("RP1", formatar_ct(ct_rp1)),
            AlvoCelula("RP2", formatar_ct(ct_rp2)),
            AlvoCelula("RP3", formatar_ct(ct_rp3)),
        ]

        classif, detect = classificar_amostra(res, rp_valido=True)
        blocos.append(
            BlocoAmostra(
                codigo=codigo,
                alvos=distribuir_alvos_grid(alvos_celulas),
                classificacao=classif,
                detectaveis=detect,
            )
        )
    return blocos


# ============================================================================
# Renderizacao em PDF
# ============================================================================


def _draw_text(c, x, y, text, size=8, bold=False, color=colors.black, anchor="left"):
    font = "Helvetica-Bold" if bold else "Helvetica"
    c.setFont(font, size)
    c.setFillColor(color)
    if anchor == "center":
        c.drawCentredString(x, y, text)
    elif anchor == "right":
        c.drawRightString(x, y, text)
    else:
        c.drawString(x, y, text)
    c.setFillColor(colors.black)


def _draw_block(c, x, y, w, h, bloco):
    # borda
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.rect(x, y, w, h, stroke=1, fill=0)

    if bloco is None:
        return

    # area do codigo (top 18%)
    codigo_h = h * 0.20
    grid_h = h * 0.55
    badge_h = h * 0.25

    # codigo (centralizado)
    _draw_text(
        c,
        x + w / 2,
        y + h - codigo_h * 0.65,
        bloco.codigo,
        size=11,
        bold=True,
        anchor="center",
    )
    # linha separadora
    c.setLineWidth(0.3)
    c.line(x, y + h - codigo_h, x + w, y + h - codigo_h)

    # grid 3x3
    alvos = list(bloco.alvos)
    while len(alvos) < 9:
        alvos.append(AlvoCelula("", ""))
    grid_top = y + h - codigo_h
    cell_w = w / 3
    cell_h = grid_h / 3
    for i in range(9):
        r = i // 3
        col = i % 3
        cx = x + col * cell_w + 2
        cy = grid_top - r * cell_h - cell_h / 2 + 2
        alvo = alvos[i]
        if alvo.nome:
            texto = (
                f"<b>{alvo.nome}</b> – {alvo.ct_formatado}"
                if alvo.ct_formatado
                else f"<b>{alvo.nome}</b> – "
            )
            style = ParagraphStyle(
                "alvo",
                fontName="Helvetica",
                fontSize=6.5,
                leading=7.5,
            )
            p = Paragraph(texto, style)
            p.wrapOn(c, cell_w - 4, cell_h)
            p.drawOn(c, cx, cy - 1)

    # badge resultado
    badge_top = y + badge_h
    if bloco.classificacao == CLASSIF_DETECTAVEL:
        fill_c = colors.black
        txt_c = colors.white
    elif bloco.classificacao == CLASSIF_INVALIDO:
        fill_c = colors.HexColor("#999999")
        txt_c = colors.black
    else:
        fill_c = colors.white
        txt_c = colors.black
    c.setFillColor(fill_c)
    c.rect(x, y, w, badge_h, stroke=1, fill=1)
    c.setFillColor(txt_c)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(x + w / 2, y + badge_h / 2 - 2.5, bloco.texto_resultado)
    c.setFillColor(colors.black)


def renderizar_pdf(mapa, caminho):
    page_w, page_h = landscape(A4)
    c = canvas.Canvas(caminho, pagesize=landscape(A4))
    c.setTitle(f"Mapa Placa {mapa.nome_exame}")

    margin = 8 * mm
    # cabecalho
    header_h = 12 * mm
    header_y = page_h - margin - header_h
    # bloco cinza com nome exame
    c.setFillColor(colors.HexColor("#E0E0E0"))
    c.rect(margin, header_y + 7 * mm, page_w - 2 * margin, 5 * mm, stroke=0, fill=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(
        page_w / 2, header_y + 8.5 * mm, mapa.nome_exame.upper()
    )

    # linha 2: placa + status
    c.setFont("Helvetica", 9)
    c.drawString(margin + 2, header_y + 2 * mm, f"Placa: {mapa.nome_placa}")
    # status
    status_text = "PLACA OK" if mapa.placa_ok else "RECOMECAR PROCESSO"
    status_w = 50 * mm
    status_x = page_w - margin - status_w
    if mapa.placa_ok:
        c.setFillColor(colors.black)
        c.rect(status_x, header_y + 1 * mm, status_w, 5 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white)
    else:
        c.setFillColor(colors.HexColor("#999999"))
        c.rect(status_x, header_y + 1 * mm, status_w, 5 * mm, stroke=0, fill=1)
        c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(status_x + status_w / 2, header_y + 2.5 * mm, status_text)
    c.setFillColor(colors.black)

    # grid de blocos
    grid_top = header_y - 2 * mm
    footer_h = 35 * mm
    grid_bottom = margin + footer_h
    grid_h = grid_top - grid_bottom
    grid_w = page_w - 2 * margin
    n_cols = mapa.blocos_por_linha
    n_rows = mapa.linhas_blocos
    bw = grid_w / n_cols
    bh = grid_h / n_rows

    for i_row, linha in enumerate(mapa.blocos):
        for i_col, bloco in enumerate(linha):
            x = margin + i_col * bw
            y = grid_top - (i_row + 1) * bh
            _draw_block(c, x + 0.5, y + 0.5, bw - 1, bh - 1, bloco)

    # rodape: controles
    footer_y = margin + footer_h - 5 * mm
    c.setFillColor(colors.HexColor("#E0E0E0"))
    c.rect(margin, footer_y, page_w - 2 * margin, 5 * mm, stroke=0, fill=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin + 2, footer_y + 1.5 * mm, "CONTROLES")

    # linha de controles
    ctrl_y = footer_y - 6 * mm
    n_ctrls = max(1, len(mapa.controles))
    ctrl_w = (page_w - 2 * margin) / max(1, min(8, n_ctrls))
    for i, ctrl in enumerate(mapa.controles[:8]):
        x = margin + i * ctrl_w
        c.setLineWidth(0.4)
        c.rect(x, ctrl_y, ctrl_w - 1, 5 * mm, stroke=1, fill=0)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(x + 2, ctrl_y + 1.5 * mm, f"{ctrl.nome} {ctrl.alvo}")
        c.setFont("Helvetica", 7)
        c.drawString(
            x + ctrl_w * 0.45, ctrl_y + 1.5 * mm,
            f"CT: {ctrl.ct_formatado or '—'}",
        )
        # V/X
        if not ctrl.valido:
            c.setFillColor(colors.HexColor("#999999"))
            c.rect(x + ctrl_w - 7 * mm, ctrl_y, 6 * mm, 5 * mm, stroke=1, fill=1)
            c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(
            x + ctrl_w - 4 * mm,
            ctrl_y + 1.5 * mm,
            "V" if ctrl.valido else "X",
        )

    # assinaturas
    sig_y = margin + 4 * mm
    c.setFont("Helvetica", 9)
    c.drawString(margin, sig_y, "Analisado por: ___________________________________")
    c.drawString(
        page_w / 2 + 2 * mm,
        sig_y,
        "Liberado por: ___________________________________",
    )

    # data de geracao
    c.setFont("Helvetica-Oblique", 7)
    c.drawRightString(
        page_w - margin,
        margin,
        f"Gerado em {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    )

    c.showPage()
    c.save()


def main():
    rng = random.Random(42)  # seed para resultado reproduzivel
    blocos = _gerar_blocos_zdc(rng, total=32)
    controles = [
        ControleQuadro("CN", "ZK", "", True),
        ControleQuadro("CN", "DEN", "", True),
        ControleQuadro("CN", "CHIK", "", True),
        ControleQuadro("CP", "ZK", "27,30", True),
        ControleQuadro("CP", "DEN", "26,80", True),
        ControleQuadro("CP", "CHIK", "28,10", True),
    ]
    mapa = montar_mapa(
        nome_exame="ZDC BioManguinhos",
        nome_placa="zdc_biom_placa_680_results_20260510",
        pocos_por_amostra=3,
        blocos_lineares=blocos,
        controles=controles,
    )

    out_dir = ROOT / "relatorios"
    out_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho_pdf = out_dir / f"exemplo_mapa_placa_ZDC_BioManguinhos_{ts}.pdf"
    renderizar_pdf(mapa, str(caminho_pdf))
    print(f"PDF gerado: {caminho_pdf}")


if __name__ == "__main__":
    main()
