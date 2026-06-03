# Forensics — T-AUD-016: import circular `envio_gal` ⇄ `ui`

- **Data:** 2026-06-01T20:55:00Z
- **Origem:** Fase 2 Audit Refactoring (anexo T-AUD-016)
- **Método:** subagente `Explore` (READ-ONLY) + leitura direta
- **Severidade:** Alto (latente; mascarado pela ordem de boot ui-first)

## 1. Cadeia exata do ciclo (confirmada por leitura)

```
exportacao/envio_gal.py:84   from ui.gal_ui_dialog_adapter import GalUIDialogAdapter
  └─> ui/gal_ui_dialog_adapter.py  (imports: customtkinter, config_service — não recicla sozinho)
  └─> ui/__init__.py:11        from .main_window import MainWindow, criar_aplicacao_principal
        └─> ui/main_window.py:31   from ui.menu_handler import MenuHandler
              └─> ui/menu_handler.py:16  from exportacao.envio_gal import abrir_janela_envio_gal
                    ✗ ImportError: cannot import name 'abrir_janela_envio_gal'
                       from partially initialized module 'exportacao.envio_gal'
```

O gatilho é o import de `ui/*` no **topo** de `envio_gal.py` (linha 84): ao importar `envio_gal`
fora de uma ordem ui-first, Python começa a inicializar `envio_gal`, encontra o import de `ui`,
inicializa o pacote `ui` (que via `__init__` puxa `main_window` → `menu_handler`), e este tenta
importar `abrir_janela_envio_gal` de um `envio_gal` ainda parcialmente inicializado → erro.

**Por que não quebra em runtime real:** `main.py` importa a UI primeiro; quando `menu_handler`
executa, `envio_gal` já está totalmente carregado. Falha apenas em ordem não-ui-first (ex.: o
comando literal do T-002 na Fase 0, ou testes que importam `envio_gal` isolado).

## 2. Uso real de `GalUIDialogAdapter` em `envio_gal.py`

| Linha | Uso |
|---|---|
| 84 | import top-level (o causador do ciclo) |
| ~1468 | `self.gal_ui_dialog_adapter = GalUIDialogAdapter()` no `__init__` de `IntegrationApp` |
| ~1619 | `self.gal_ui_dialog_adapter.collect(self._dialog_parent())` em `selecionar_csv()` (callback de UI) |

O símbolo **não é necessário em tempo de import** — só na instanciação de `IntegrationApp` (que já
ocorre após o boot da UI). **Viabilidade de lazy import: ALTA.**

## 3. Opções de fix (TEXTO — não aplicar nesta fase)

| Opção | Descrição | Prós | Contras | Esforço |
|---|---|---|---|---|
| **A — Lazy import** | Mover `from ui.gal_ui_dialog_adapter import GalUIDialogAdapter` para dentro do `__init__` de `IntegrationApp` | Quebra o ciclo imediatamente; mínima alteração; reversível | Import "escondido" no método; padrão menos explícito | ~5 min |
| **B — Inversão via Port** | `envio_gal` depende de um `Protocol GalDialogCollector` (módulo puro); implementação `GalUIDialogAdapter` injetada/lazy | Desacopla de UI concreta; testável sem Selenium; SOLID; resolve permanentemente | Novo módulo de contrato; altera assinatura/injeção; toca testes | ~30-45 min |
| **C — Extração de módulo UI** | Mover `IntegrationApp`/`abrir_janela_envio_gal` para `exportacao/envio_gal_ui.py`; `envio_gal.py` fica sem UI | Separação lógica/UI estrutural; SRC; re-export para compat | Refatoração grande (~800-1000 linhas movidas); toca vários callers | ~90-120 min |

## 4. Recomendação para Fase 6

Alinhado a ADR-A6 / Spec US-6 (injeção de `_default_webdriver_factory` e dependências de UI via
Port): preferir **Opção B (inversão via Port/Protocol)** como solução canônica de longo prazo,
pois converge com a estratégia de portas já planejada para o módulo GAL e habilita
GAL-PEND-002 (testes sem Selenium real). A **Opção A (lazy import)** é aceitável como mitigação
imediata de baixo risco, caso a Fase 6 precise de um passo intermediário antes da refatoração por
Port. Em qualquer caso: **cobertura de teste do ciclo (importar `envio_gal` isolado) deve preceder
a mudança.**

**Próxima ação:** endereçar em Fase 6 (T-061), ao integrar `assert_valid_gal_payload` em
`envio_gal.enviar_amostra`. Não-bloqueante para Fases 2-5.
