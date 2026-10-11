# Pomodoro

Um timer Pomodoro discreto para estudar no Linux (GNOME). Ele fica como uma pílula
pequena no topo da tela, logo abaixo do relógio, e só vira um cartão completo quando
você clica nele.

- **25 min de foco, 5 min de pausa.** Quando uma fase termina, toca um sino suave e o
  cartão abre sozinho. A próxima fase só começa quando você clica em **Começar**, ou em
  **Depois** se ainda estiver terminando uma questão.
- **Discreto:** a pílula fica levemente translúcida, nunca rouba o foco da janela em que
  você está lendo e não cobre a barra do GNOME.
- **Arrastável:** arraste a pílula para onde quiser e ela lembra a posição. Botão
  direito → *Voltar ao topo* para voltar ao lugar padrão.
- **Hoje:** mostra os pomodoros concluídos no dia e os minutos de foco.

Visual em creme, argila e sálvia, com numerais em Source Serif 4 e textos em Inter.

## Requisitos

- Linux com X11 (testado no Ubuntu com GNOME)
- [uv](https://docs.astral.sh/uv/)
- `pw-play` (PipeWire), `paplay` ou `aplay` para o som; sem nenhum deles o app só fica
  em silêncio

## Instalar e rodar

```bash
git clone https://github.com/dame9177/pomodoro.git
cd pomodoro
uv sync
uv run pomodoro
```

Para colocar no menu de aplicativos (e, se quiser, abrir junto com o login):

```bash
./scripts/install-desktop.sh              # menu de aplicativos
./scripts/install-desktop.sh --autostart  # menu + iniciar com a sessão
```

Abrir o app de novo com ele já rodando só traz o cartão para a frente.

## Atalhos (com o cartão aberto)

| Tecla | Ação |
|---|---|
| Espaço / Enter | pausar, retomar ou começar a próxima fase |
| Esc | recolher |

## Configuração

`~/.config/pomodoro/settings.json` é criado na primeira vez que você arrasta a pílula:

```json
{
  "focus_seconds": 1500,
  "break_seconds": 300,
  "position": [1220, 44],
  "notifications": false
}
```

- `notifications`: `true` também envia uma notificação do GNOME no fim de cada fase. Vem
  desligado porque o banner aparece no mesmo lugar onde o cartão abre.
- O histórico do dia fica em `~/.local/share/pomodoro/history.json`.

Para testar o fluxo rapidamente: `POMODORO_FOCUS_SECONDS=20 POMODORO_BREAK_SECONDS=10 uv run pomodoro`.

## Desenvolvimento

```bash
uv run pytest
```

O núcleo (`timer`, `stats`, `settings`, `placement`) não depende do Qt e é testado
isoladamente. A janela é pintada à mão com QPainter em `src/pomodoro/ui/window.py`.

## Licença

MIT. As fontes incluídas (Source Serif 4 e Inter) usam a SIL Open Font License 1.1 e
estão em `src/pomodoro/assets/fonts/` com suas licenças.
