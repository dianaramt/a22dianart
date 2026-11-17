# Bambi

**Books, Archives, Media & Bibliographic Information**

## Descripción

Bambi é unha proposta de aplicación web para que librerías independentes e bibliotecas pequenas teñan un escaparate dixital propio e poidan ofrecer consulta de catálogo e reservas para recoller presencialmente. Os centros poden personalizar a súa páxina e subir os libros que se poden reservar. Mentras que os lectores buscan títulos, consultan dispoñibilidade e reservan. O proxecto contempla perfís diferenciados, regras de fiabilidade e unha interface personalizable en galego, castelán e inglés.

O obxectivo académico é desenvolver un prototipo funcional despregado con datos ficticios entre setembro e decembro de 2026.

## Execución/Posta en marcha

### Requisitos

- Python 3.12 ou superior (desenvolvido con Python 3.14 e Django 6.1)
- Git

### Posta en marcha con Docker (unha soa instrución)

Só precisa [Docker](https://docs.docker.com/get-docker/) (en Windows e macOS, Docker Desktop aberto). Desde un clon do repositorio:

```bash
docker compose up
```

Isto constrúe a imaxe de Django, arranca PostgreSQL, aplica as migracións e, a primeira vez, carga os datos de demostración. A aplicación queda en <http://localhost:8000/> coas [contas de demostración](#contas-de-demostración).

- Non fai falta ningún `.env`. Se queres outro nome de base de datos, usuario ou contrasinal, defíneos no `.env` (ver [.env.example](.env.example)) antes do primeiro arranque.
- Os datos gárdanse en volumes de Docker e consérvanse entre arranques. Para empezar de cero: `docker compose down -v`.
- Tras cambiar o código ou `requirements.txt`: `docker compose up --build`.
- Tests dentro do contedor (contra PostgreSQL): `docker compose exec web python manage.py test`.

Este modo é só para uso local (`DEBUG=True`). A versión publicada está en PythonAnywhere, porque o plan gratuíto non executa contedores (ver [doc/despregamento.md](doc/despregamento.md)).

### Instalación en desenvolvemento (sen Docker)

#### Windows

Os comandos están escritos para Git Bash.

```bash
git clone <url-do-repositorio>
cd a22dianart

# Contorno virtual e dependencias
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt

# Base de datos (SQLite en desenvolvemento)
python manage.py migrate

# Opcional: datos ficticios de demostración (centros, libros, usuarios e reservas)
python manage.py cargar_demo

# Servidor de desenvolvemento
python manage.py runserver
```

#### Linux

Exemplo para Debian/Ubuntu:

```bash
# Python, venv, Git e gettext
sudo apt update
sudo apt install python3 python3-venv python3-pip git gettext

git clone <url-do-repositorio>
cd a22dianart

# Contorno virtual e dependencias
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Base de datos (SQLite en desenvolvemento)
python manage.py migrate

# Opcional: datos ficticios de demostración (centros, libros, usuarios e reservas)
python manage.py cargar_demo

# Servidor de desenvolvemento
python manage.py runserver
```

Co contorno virtual activado, `python` xa apunta ao Python do `.venv`, así que non fai falta escribir `python3`.

A aplicación queda dispoñible en <http://127.0.0.1:8000/>.

Para ter unha conta propia de superusuario (tamén dá acceso ao admin de Django en `/admin/`):

```bash
python manage.py createsuperuser           # Linux, macOS e PowerShell
winpty python manage.py createsuperuser    # Git Bash en Windows
```

### Contas de demostración

Despois de `python manage.py cargar_demo`, todas as contas teñen o contrasinal `Demo-Bambi-2026` (só en desenvolvemento; en produción é obrigatorio definir `BAMBI_DEMO_CONTRASINAL`):

| Rol                     | Correo                        |
| ----------------------- | ----------------------------- |
| Superusuario            | `plataforma@demo.bambi.test`  |
| Administrador de centro | `castineiros@demo.bambi.test` |
| Administrador de centro | `andaina@demo.bambi.test`     |
| Lector                  | `lucia@demo.bambi.test`       |

Para borrar só os datos de demostración: `python manage.py cargar_demo --borrar`.

### Caducidade das reservas

As reservas que pasan o prazo de recollida péchanse co comando:

```bash
python manage.py caducar_reservas
```

Libera os exemplares e suma un punto de penalización a cada lector afectado. En produción execútase unha vez ao día como tarefa programada (ver [doc/despregamento.md](doc/despregamento.md)). Con Docker: `docker compose exec web python manage.py caducar_reservas`.

As regras de fiabilidade están en `bambi/settings.py` (`BAMBI_PUNTOS_*` e `BAMBI_DIAS_BLOQUEO`): cada reserva non recollida ou caducada suma 1 punto, cada recollida resta 1, e con 3 puntos o lector non pode reservar durante 14 días.

### Tests

```bash
python manage.py test
```

### Traducións

Os textos escríbense en galego no código (`{% translate %}` nas plantillas e `_()` en Python) e tradúcense ao castelán e ao inglés en `locale/es` e `locale/en`. Tras engadir ou cambiar textos hai que executar os comandos seguintes. Precisan GNU gettext: en Windows vén incluído en Git for Windows (executar desde Git Bash); en Linux instálase co paquete `gettext`.

```bash
python manage.py makemessages -l es -l en --ignore=".venv/*" --ignore="static/*"
# completar as novas entradas msgstr en locale/*/LC_MESSAGES/django.po
python manage.py compilemessages --ignore=".venv/*"
```

### Variables de contorno

Lense do sistema ou dun ficheiro `.env` na raíz do proxecto (exemplo en [.env.example](.env.example)). En desenvolvemento non fai falta definir ningunha. A táboa recolle os valores de produción en PythonAnywhere. A clave e o contrasinal non se publican: xéranse e gárdanse só no `.env` do servidor.

| Variable                 | Uso                                                       | Valor en produción                                                        |
| ------------------------ | --------------------------------------------------------- | ------------------------------------------------------------------------- |
| `DJANGO_DEBUG`           | Modo depuración                                           | `False`                                                                   |
| `DJANGO_SECRET_KEY`      | Clave secreta de Django                                   | Xerada con `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_ALLOWED_HOSTS`   | Dominios desde os que se serve a web, separados por comas | `a22dianart.pythonanywhere.com`                                           |
| `DJANGO_SSL_REDIRECT`    | Redirixe todo o tráfico HTTP a HTTPS                      | `True`                                                                    |
| `BAMBI_DEMO_CONTRASINAL` | Contrasinal das contas creadas por `cargar_demo`          | Contrasinal propio e longo (só se se carga a demo)                        |

Variables de PostgreSQL, só para Docker en local. Django usa PostgreSQL só se existe `POSTGRES_HOST` (defínea o `compose.yaml`); se non, usa SQLite, tanto en desenvolvemento sen Docker como en PythonAnywhere.

| Variable            | Uso                                        | Valor por defecto no compose |
| ------------------- | ------------------------------------------ | ---------------------------- |
| `POSTGRES_DB`       | Nome da base de datos                      | `bambi`                      |
| `POSTGRES_USER`     | Usuario de PostgreSQL                      | `bambi`                      |
| `POSTGRES_PASSWORD` | Contrasinal de PostgreSQL                  | `bambi-local`                |
| `POSTGRES_HOST`     | Servidor de PostgreSQL (o compose pon `db`) | Sen definir fóra de Docker   |
| `POSTGRES_PORT`     | Porto de PostgreSQL                        | `5432`                       |

## Uso

Con bambi podemos ver os diferentes escaparates das librarías e bibliotecas da túa contorna, buscar o libro que nos interesa e comprobar se está dispoñible antes de ir presencialmente. Se o está, poderase reservar para recollelo no propio centro. Así, este proxecto apoia o comercio e a cultura locais. Bambi estará dispoñible en galego, castelán e inglés. Todo esto nunha interface amigable e accesible para o usuario e perfectamente adaptable á imaxe de cada centro.

## Sobre a autora

Son Diana Ramos Torrado, estudante de programación web. Este proxecto nace co prósito de presentar un traballo final que reúna por un lado a miña pasión pasión polo front-end e por outro, o gusto da linguaxe python (de aí o uso de Django para este proxecto). Ademais, gustaríame amosar con este que si que se poden facer webs simples visualmente ao mesmo tempo que atractivas sen perder a usabilidade.

## Licenza

O repositorio de momento inclúe [MIT License](LICENSE).

## Documentación

Toda a documentación do proxecto de forma máis detallada atópase en:
[Análise do proxecto](doc/doc.md)

## Guía de contribución

Ata o final da primeira fase do proxecto, na que se incluirán as funcionalidades principais, non se poderá contribuir ao proxecto. Posteriormente poderase contribuir con parches das diferentes accións que leva a cabo a plataforma.
O código estará accesible nun repositorio público en GitHub.
