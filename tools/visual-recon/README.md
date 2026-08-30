# Sistema de Analise e Reconstrucao Visual

Pipeline de visao computacional que analisa videos de referencia e extrai o
conhecimento necessario para reconstruir a interface com fidelidade: estrutura,
design system, animacoes e sensacao de uso.

## Por que existe

Analisar screenshots soltos perde exatamente o que importa numa interface: como
as coisas se movem. Este sistema analisa a **sequencia completa** de frames no
FPS nativo e mede duracao, direcao, aceleracao e curva de cada animacao.

## Instalacao

Ja instalado. O ambiente isolado fica em `.venv-visual/` (na raiz do projeto) e
contem OpenCV, scikit-learn, numpy e Pillow. O Python global do sistema nao foi
alterado.

Requer FFmpeg no PATH (ja disponivel).

Para recriar do zero:

```bash
python -m venv .venv-visual
./.venv-visual/Scripts/python.exe -m pip install opencv-python-headless scikit-learn numpy pillow
```

## Uso rapido

```bash
P=./.venv-visual/Scripts/python.exe
C=tools/visual-recon/vrecon_cli.py

# analisar um video de referencia
$P $C analisar caminho/do/video.mp4 --titulo "App Fintech" --tags "mobile,dark"

# ver o que ja foi analisado
$P $C listar

# recuperar uma referencia
$P $C carregar "App Fintech" --secao tudo

# tokens de design prontos para uso
$P $C tokens "App Fintech" --categoria color

# buscar padroes de animacao reutilizaveis entre todas as referencias
$P $C buscar-animacoes --easing ease-out --max-duracao 400

# validar a reconstrucao contra a referencia
$P $C comparar "App Fintech" minha-versao.mp4
```

## Comandos do Claude Code

| Comando | Funcao |
|---|---|
| `/analisar-video` | Analisa um video e grava na memoria visual |
| `/carregar-memoria-visual` | Recupera uma referencia ja analisada |
| `/reconstruir-interface` | Reconstroi a UI usando a referencia |
| `/comparar-referencia` | Compara o resultado e corrige divergencias |
| `/usar-design-system` | Aplica os tokens extraidos no codigo |

## Arquitetura

```
tools/visual-recon/
  vrecon_cli.py          interface de linha de comando
  vrecon/
    config.py            limiares e caminhos (tuning centralizado)
    extraction.py        [1] frames no FPS nativo + perfil de mudanca
    temporal.py          [2] optical flow, velocidade, curvas de easing
    components.py        [3] deteccao de componentes + arvore hierarquica
    design.py            [4] cores, tipografia, layout, efeitos
    animation.py         [5] engenharia reversa -> spec + CSS + Framer Motion
    memory.py            [6] persistencia (SQLite + JSON)
    validation.py        [8] comparacao referencia x gerado
    pipeline.py          orquestrador das etapas
```

## O que fica salvo

```
visual-memory/
  index.db                          indice SQLite (busca rapida)
  videos/<slug>/
    analysis.json                   analise completa
    REPORT.md                       relatorio legivel / briefing
    design-tokens.css               tokens prontos para importar
    animations.css                  keyframes prontos para usar
    keyframes/                      frames representativos
    frames/                         sequencia completa (nao versionada)
```

## Decisoes tecnicas relevantes

**Deteccao de mudanca por regiao, nao por media global.** Um card animado ocupa
uma fracao pequena de uma tela 1080x1920; a media do frame inteiro afogaria o
movimento no ruido de compressao. O sistema mede a celula mais alterada de uma
grade 8x8, o que tambem indica *onde* na tela a animacao acontece.

**Histerese na deteccao de animacao.** Curvas ease-out terminam de forma
assintotica: os ultimos frames andam fracoes de pixel. Sem histerese, a cauda e
cortada e a duracao medida sai curta demais. O corte e ancorado no piso de
ruido, nao numa fracao do pico (a cauda e, por definicao, uma fracao pequena do
pico).

**Spring exige overshoot real.** Uma mola reacelera depois de desacelerar; uma
ease-out apenas decai. A deteccao exige um vale seguido de repique claro, com
margem folgada acima do ruido de quantizacao — do contrario toda ease-out com
cauda ruidosa seria classificada como spring.

**Cortes de cena usam a media global.** Numa troca de tela a imagem inteira
muda; e o unico caso em que a media global e o sinal certo.

## Precisao medida

Validado contra um video sintetico com valores conhecidos (fixture com animacao
de 350ms ease-out-cubic, translateY 40px, corte de cena em t=1.4s):

| Medida | Real | Detectado |
|---|---|---|
| Resolucao / FPS | 1080x1920 @ 60 | exato |
| Frames extraidos | 114 | 114 |
| Corte de cena | frame 84 | frame 84 |
| Inicio da animacao | frame 30 | frame 30 |
| Duracao | 350ms | 317ms (-9%) |
| Direcao | para cima | cima |
| Perfil | desaceleracao | desacelerando |
| Curva | ease-out cubic | ease-out quad |
| translateY | 40px | 30px (-25%) |
| Margem lateral | 48px | 46px |
| Padding do container | 32px | 32px |
| Largura de conteudo | 984px | 988px |
| Unidade base de espacamento | 4px | 4px |
| Tema / fundo | escuro | escuro |

O comparador tambem foi validado contra uma reconstrucao com defeitos
plantados de proposito (cor de acento trocada, animacao de 800ms linear no
lugar de 350ms ease-out, bottom nav removida, margem alterada). Ele reprovou
com 44,9% e apontou cada divergencia com o ajuste correspondente.

As subestimativas tem causa conhecida: o optical flow mede o deslocamento medio
do campo, nao o pico do objeto, e os ultimos frames de uma ease-out sao
sub-pixel (fisicamente nao mensuraveis). Para reconstrucao isso e aceitavel — a
familia da curva e a ordem de grandeza estao corretas. Se precisar do valor
exato de translate, ajuste a olho depois de comparar.

## Limitacoes honestas

- **Nao le texto.** Detecta regioes de texto e estima tamanho de fonte pela
  geometria, mas nao faz OCR nem identifica a familia tipografica.
- **Nao separa objetos individuais.** O optical flow e denso (campo inteiro);
  dois elementos se movendo em direcoes diferentes no mesmo segmento sao
  reportados como um movimento medio.
- **Raio de borda e estimado**, nao medido geometricamente.
- **Glassmorphism e heuristico** (baixa nitidez local + variacao de cor); pode
  confundir com imagem desfocada de fundo.
- **Videos com compressao agressiva** elevam o piso de ruido e podem exigir
  ajuste de `change_threshold` em `config.py`.
