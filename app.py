from datetime import datetime
import html
import os
import sqlite3

from flask import Flask, Response, abort, redirect, render_template_string, request


app = Flask(__name__)
DB = "dados.db"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")


# ---------------------------------------------------------------------------
# Banco
# ---------------------------------------------------------------------------

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")

    con.execute("""
        CREATE TABLE IF NOT EXISTS notas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_registro TEXT NOT NULL
                CHECK (tipo_registro IN ('changelog', 'futuro')),
            tipo TEXT NOT NULL
                CHECK (tipo IN ('novo', 'alteracao', 'correcao')),
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'proposto',
            referencia TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS comentarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nota_id INTEGER NOT NULL,
            parent_id INTEGER,
            autor TEXT,
            email TEXT,
            telefone TEXT,
            texto TEXT NOT NULL,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (nota_id)
                REFERENCES notas(id) ON DELETE CASCADE,

            FOREIGN KEY (parent_id)
                REFERENCES comentarios(id) ON DELETE CASCADE
        )
    """)

    # Compatibilidade com dados.db de versões anteriores.
    colunas = {row["name"] for row in con.execute("PRAGMA table_info(comentarios)")}

    for nome, tipo in (
        ("parent_id", "INTEGER"),
        ("email", "TEXT"),
        ("telefone", "TEXT"),
    ):
        if nome not in colunas:
            con.execute(f"ALTER TABLE comentarios ADD COLUMN {nome} {tipo}")

    return con


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def esc(valor):
    return html.escape(str(valor or ""))


def normalizar_parent_id(valor):
    """
    Bancos antigos podem ter parent_id como TEXT ("12").
    Converter para int evita o bug de respostas não encontrarem seus pais.
    """
    if valor in (None, ""):
        return None

    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def admin_auth():
    auth = request.authorization

    if auth and auth.password == ADMIN_PASSWORD:
        return None

    return Response(
        "Autenticação necessária.",
        401,
        {"WWW-Authenticate": 'Basic realm="Administração"'},
    )


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CSS = """
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: #fff;
    color: #111827;
    font: 15px system-ui, -apple-system, "Segoe UI", sans-serif;
}

aside {
    position: fixed;
    width: 220px;
    height: 100vh;
    padding: 70px 18px;
    background: #fafafa;
    border-right: 1px solid #eee;
}

aside a {
    display: block;
    margin: 4px 0;
    padding: 12px 14px;
    border-radius: 8px;
    color: #4b5563;
    text-decoration: none;
}

aside a.on {
    background: #eee;
    color: #111827;
    font-weight: 600;
}

main {
    margin-left: 220px;
    max-width: 1050px;
    padding: 70px 60px;
}

h1 {
    margin: 0 0 8px;
    font-size: 32px;
}

h2 {
    margin: 46px 0 20px;
    font-size: 22px;
}

.sub,
.muted {
    color: #6b7280;
}

.sub {
    margin: 0 0 40px;
}

.item {
    display: grid;
    grid-template-columns: 120px 1fr auto;
    gap: 22px;
    align-items: start;
    margin-bottom: 30px;
}

.tag {
    display: inline-block;
    padding: 7px 12px;
    border-radius: 10px;
    background: #f0f1f3;
    color: #4b5563;
    font-size: 12px;
    font-weight: 600;
}

.title {
    color: #111827;
    font-size: 17px;
    font-weight: 600;
    text-decoration: none;
}

.desc,
.comment-text {
    margin-top: 4px;
    color: #6b7280;
    line-height: 1.5;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
}

.comments,
.link,
.admin-note {
    color: #6b7280;
    text-decoration: none;
}

.comments {
    white-space: nowrap;
}

form {
    max-width: 760px;
}

.field {
    width: 100%;
    margin-bottom: 10px;
    padding: 10px 12px;
    border: 1px solid #ddd;
    border-radius: 7px;
    font: inherit;
}

button,
.btn {
    padding: 9px 14px;
    border: 0;
    border-radius: 7px;
    background: #111827;
    color: #fff;
    cursor: pointer;
    font: inherit;
    text-decoration: none;
}

.comment {
    margin: 24px 0;
}

.comment-meta {
    display: flex;
    gap: 8px;
    align-items: baseline;
}

.comment small {
    color: #9ca3af;
}

.replies {
    margin-left: 28px;
    padding-left: 18px;
    border-left: 2px solid #f1f1f1;
}

.reply-link {
    margin-top: 7px;
    padding: 0;
    background: none;
    color: #6b7280;
    font-size: 13px;
}

.reply-form {
    display: none;
    margin: 10px 0;
}

.reply-form.open {
    display: block;
}

.contact {
    margin: 6px 0;
    color: #6b7280;
    font-size: 12px;
}

.admin-comment {
    padding: 16px 0;
    border-bottom: 1px solid #eee;
}

.admin-note {
    color: #374151;
    font-weight: 600;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th,
td {
    padding: 10px 8px;
    border-bottom: 1px solid #eee;
    text-align: left;
    vertical-align: top;
}

.actions {
    display: flex;
    gap: 8px;
}

.danger {
    padding: 0;
    background: none;
    color: #b42318;
}

@media (max-width: 720px) {
    aside {
        position: static;
        display: flex;
        gap: 6px;
        width: auto;
        height: auto;
        padding: 14px;
        border-right: 0;
        border-bottom: 1px solid #eee;
    }

    aside a {
        margin: 0;
    }

    main {
        margin: 0;
        padding: 32px 20px;
    }

    .item {
        grid-template-columns: 100px 1fr;
    }

    .comments {
        grid-column: 2;
    }

    .replies {
        margin-left: 12px;
        padding-left: 12px;
    }
}
"""


# ---------------------------------------------------------------------------
# HTML base
# ---------------------------------------------------------------------------

BASE = """
<!doctype html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title }}</title>

    <style>
""" + CSS + """
    </style>
</head>

<body>
    <aside>
        <a class="{{ 'on' if page == 'updates' else '' }}" href="/updates">
            Atualizações
        </a>

        <a class="{{ 'on' if page == 'futuros' else '' }}" href="/futuros">
            Futuros
        </a>
    </aside>

    <main>
        {{ body | safe }}
    </main>

    <script>
        function responder(id) {
            document
                .getElementById("resposta-" + id)
                .classList.toggle("open");
        }
    </script>
</body>
</html>
"""


def pagina(body, title="What's New", page=""):
    return render_template_string(BASE, body=body, title=title, page=page)


# ---------------------------------------------------------------------------
# Feed
# ---------------------------------------------------------------------------

@app.get("/")
def home():
    return redirect("/updates")


@app.get("/updates")
@app.get("/futuros")
def feed():
    futuro = request.path == "/futuros"
    tipo_registro = "futuro" if futuro else "changelog"

    con = db()
    notas = con.execute(
        """
        SELECT
            n.*,
            COUNT(c.id) AS comentarios
        FROM notas AS n
        LEFT JOIN comentarios AS c
            ON c.nota_id = n.id
        WHERE n.tipo_registro = ?
        GROUP BY n.id
        ORDER BY n.criado_em DESC, n.id DESC
        """,
        (tipo_registro,),
    ).fetchall()
    con.close()

    grupos = {}
    for nota in notas:
        grupos.setdefault(nota["criado_em"][:10], []).append(nota)

    titulo = "Futuros" if futuro else "Atualizações"
    subtitulo = (
        "Ideias e melhorias futuras."
        if futuro
        else "Histórico de mudanças do projeto."
    )

    body = f"""
        <h1>{titulo}</h1>
        <p class="sub">{subtitulo}</p>
    """

    labels = {
        "novo": "NOVO",
        "alteracao": "ALTERAÇÃO",
        "correcao": "CORREÇÃO",
    }

    for data, itens in grupos.items():
        data_formatada = datetime.strptime(data, "%Y-%m-%d").strftime("%d/%m/%Y")
        body += f"<h2>{data_formatada}</h2>"

        for nota in itens:
            status = ""

            if futuro:
                texto_status = nota["status"].replace("_", " ").capitalize()
                status = f"""
                    <div class="muted" style="margin-top: 6px">
                        {esc(texto_status)}
                    </div>
                """

            body += f"""
                <div class="item">
                    <div>
                        <span class="tag">{labels[nota["tipo"]]}</span>
                    </div>

                    <div>
                        <a class="title" href="/item/{nota["id"]}">
                            {esc(nota["titulo"])}
                        </a>

                        <div class="desc">{esc(nota["descricao"])}</div>
                        {status}
                    </div>

                    <a
                        class="comments"
                        href="/item/{nota["id"]}#comentarios"
                    >
                        💬 {nota["comentarios"]}
                    </a>
                </div>
            """

    if not notas:
        body += '<p class="muted">Nenhum registro.</p>'

    return pagina(body, titulo, "futuros" if futuro else "updates")


# ---------------------------------------------------------------------------
# Comentários
# ---------------------------------------------------------------------------

def form_resposta(comentario):
    return f"""
        <button
            class="reply-link"
            type="button"
            onclick="responder({comentario["id"]})"
        >
            Responder
        </button>

        <form
            id="resposta-{comentario["id"]}"
            class="reply-form"
            method="post"
            action="/comentar/{comentario["nota_id"]}"
        >
            <input
                type="hidden"
                name="parent_id"
                value="{comentario["id"]}"
            >

            <input
                class="field"
                name="autor"
                maxlength="80"
                placeholder="Seu nome (opcional)"
            >

            <input
                class="field"
                type="email"
                name="email"
                maxlength="150"
                placeholder="E-mail (opcional, não será exibido)"
            >

            <input
                class="field"
                name="telefone"
                maxlength="30"
                placeholder="Telefone (opcional, não será exibido)"
            >

            <textarea
                class="field"
                name="texto"
                rows="3"
                maxlength="3000"
                placeholder="Escreva sua resposta..."
                required
            ></textarea>

            <button>Responder</button>
        </form>
    """


def comentario_html(comentario, filhos):
    """
    Renderização recursiva:
    comentário -> resposta -> resposta da resposta -> ...
    """
    respostas = "".join(
        comentario_html(resposta, filhos)
        for resposta in filhos.get(comentario["id"], [])
    )

    bloco_respostas = (
        f'<div class="replies">{respostas}</div>'
        if respostas
        else ""
    )

    return f"""
        <div class="comment" id="comentario-{comentario["id"]}">
            <div class="comment-meta">
                <strong>{esc(comentario["autor"]) or "Anônimo"}</strong>
                <small>{esc(comentario["criado_em"][:16])}</small>
            </div>

            <div class="comment-text">{esc(comentario["texto"])}</div>

            {form_resposta(comentario)}
            {bloco_respostas}
        </div>
    """


@app.get("/item/<int:id>")
def item(id):
    con = db()

    nota = con.execute(
        """
        SELECT *
        FROM notas
        WHERE id = ?
        """,
        (id,),
    ).fetchone()

    if not nota:
        con.close()
        abort(404)

    comentarios = con.execute(
        """
        SELECT *
        FROM comentarios
        WHERE nota_id = ?
        ORDER BY criado_em, id
        """,
        (id,),
    ).fetchall()

    con.close()

    filhos = {}
    for comentario in comentarios:
        pai = normalizar_parent_id(comentario["parent_id"])
        filhos.setdefault(pai, []).append(comentario)

    arvore = "".join(
        comentario_html(comentario, filhos)
        for comentario in filhos.get(None, [])
    )

    if not arvore:
        arvore = '<p class="muted">Nenhum comentário ainda.</p>'

    labels = {
        "novo": "NOVO",
        "alteracao": "ALTERAÇÃO",
        "correcao": "CORREÇÃO",
    }

    referencia = ""
    if nota["referencia"]:
        referencia = f"""
            <p>
                <a
                    class="link"
                    target="_blank"
                    rel="noopener noreferrer"
                    href="{esc(nota["referencia"])}"
                >
                    Ver referência ↗
                </a>
            </p>
        """

    voltar = "/futuros" if nota["tipo_registro"] == "futuro" else "/updates"

    body = f"""
        <p><a class="link" href="{voltar}">← Voltar</a></p>

        <p>
            <span class="tag">{labels[nota["tipo"]]}</span>
        </p>

        <h1>{esc(nota["titulo"])}</h1>
        <div class="desc">{esc(nota["descricao"])}</div>

        {referencia}

        <section id="comentarios">
            <h2>Comentários</h2>
            {arvore}

            <h2>Comentar</h2>

            <form method="post" action="/comentar/{id}">
                <input
                    class="field"
                    name="autor"
                    maxlength="80"
                    placeholder="Seu nome (opcional)"
                >

                <input
                    class="field"
                    type="email"
                    name="email"
                    maxlength="150"
                    placeholder="E-mail (opcional, não será exibido)"
                >

                <input
                    class="field"
                    name="telefone"
                    maxlength="30"
                    placeholder="Telefone (opcional, não será exibido)"
                >

                <textarea
                    class="field"
                    name="texto"
                    rows="4"
                    maxlength="3000"
                    placeholder="Escreva um comentário..."
                    required
                ></textarea>

                <button>Comentar</button>

                <p class="muted">
                    Você pode comentar anonimamente.
                    E-mail e telefone são opcionais e ficam visíveis
                    apenas para a administração.
                </p>
            </form>
        </section>
    """

    return pagina(
        body,
        esc(nota["titulo"]),
        "futuros" if nota["tipo_registro"] == "futuro" else "updates",
    )


@app.post("/comentar/<int:id>")
def comentar(id):
    autor = request.form.get("autor", "").strip()[:80] or "Anônimo"
    email = request.form.get("email", "").strip()[:150] or None
    telefone = request.form.get("telefone", "").strip()[:30] or None
    texto = request.form.get("texto", "").strip()[:3000]

    pai = request.form.get("parent_id")

    if not texto:
        abort(400)

    if pai:
        try:
            pai = int(pai)
        except ValueError:
            abort(400)
    else:
        pai = None

    con = db()

    if not con.execute(
        "SELECT 1 FROM notas WHERE id = ?",
        (id,),
    ).fetchone():
        con.close()
        abort(404)

    if pai and not con.execute(
        """
        SELECT 1
        FROM comentarios
        WHERE id = ? AND nota_id = ?
        """,
        (pai, id),
    ).fetchone():
        con.close()
        abort(400)

    # SQL parametrizado: conteúdo do usuário nunca é concatenado no SQL.
    con.execute(
        """
        INSERT INTO comentarios (
            nota_id,
            parent_id,
            autor,
            email,
            telefone,
            texto
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (id, pai, autor, email, telefone, texto),
    )

    con.commit()
    con.close()

    return redirect(f"/item/{id}#comentarios")


# ---------------------------------------------------------------------------
# Administração
# ---------------------------------------------------------------------------

def option(nota, campo, valor, texto):
    selected = "selected" if nota and nota[campo] == valor else ""
    return f'<option value="{valor}" {selected}>{texto}</option>'


@app.route("/admin", methods=["GET", "POST"])
def admin():
    resposta = admin_auth()
    if resposta:
        return resposta

    con = db()

    if request.method == "POST":
        id_nota = request.form.get("id")

        dados = (
            request.form["tipo_registro"],
            request.form["tipo"],
            request.form["titulo"].strip(),
            request.form.get("descricao", "").strip(),
            request.form.get("status", "proposto"),
            request.form.get("referencia", "").strip() or None,
        )

        if id_nota:
            con.execute(
                """
                UPDATE notas
                SET
                    tipo_registro = ?,
                    tipo = ?,
                    titulo = ?,
                    descricao = ?,
                    status = ?,
                    referencia = ?
                WHERE id = ?
                """,
                dados + (id_nota,),
            )
        else:
            con.execute(
                """
                INSERT INTO notas (
                    tipo_registro,
                    tipo,
                    titulo,
                    descricao,
                    status,
                    referencia
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                dados,
            )

        con.commit()
        con.close()
        return redirect("/admin")

    editar = request.args.get("editar")
    nota = (
        con.execute(
            "SELECT * FROM notas WHERE id = ?",
            (editar,),
        ).fetchone()
        if editar
        else None
    )

    notas = con.execute("""
        SELECT
            n.*,
            COUNT(c.id) AS comentarios
        FROM notas AS n
        LEFT JOIN comentarios AS c
            ON c.nota_id = n.id
        GROUP BY n.id
        ORDER BY n.criado_em DESC, n.id DESC
    """).fetchall()

    comentarios = con.execute("""
        SELECT
            c.*,
            n.titulo,
            n.tipo_registro
        FROM comentarios AS c
        JOIN notas AS n
            ON n.id = c.nota_id
        ORDER BY c.criado_em DESC, c.id DESC
    """).fetchall()

    con.close()

    titulo_atual = esc(nota["titulo"]) if nota else ""
    descricao_atual = esc(nota["descricao"]) if nota else ""
    referencia_atual = (
        esc(nota["referencia"])
        if nota and nota["referencia"]
        else ""
    )

    body = f"""
        <h1>Administração</h1>
        <p class="sub">Atualizações, futuros e moderação.</p>

        <form method="post">
            <input
                type="hidden"
                name="id"
                value="{nota["id"] if nota else ""}"
            >

            <select class="field" name="tipo_registro">
                {option(nota, "tipo_registro", "changelog", "Atualização")}
                {option(nota, "tipo_registro", "futuro", "Futuro")}
            </select>

            <select class="field" name="tipo">
                {option(nota, "tipo", "novo", "Novo")}
                {option(nota, "tipo", "alteracao", "Alteração")}
                {option(nota, "tipo", "correcao", "Correção")}
            </select>

            <input
                class="field"
                name="titulo"
                placeholder="Título"
                required
                value="{titulo_atual}"
            >

            <textarea
                class="field"
                name="descricao"
                rows="5"
                placeholder="Descrição"
            >{descricao_atual}</textarea>

            <select class="field" name="status">
                {option(nota, "status", "proposto", "Proposto")}
                {option(nota, "status", "em_andamento", "Em andamento")}
                {option(nota, "status", "concluido", "Concluído")}
                {option(nota, "status", "cancelado", "Cancelado")}
            </select>

            <input
                class="field"
                name="referencia"
                placeholder="Link de referência (opcional)"
                value="{referencia_atual}"
            >

            <button>{"Salvar" if nota else "Adicionar"}</button>
            {'<a class="btn" href="/admin">Cancelar</a>' if nota else ''}
        </form>

        <h2>Registros</h2>

        <table>
            <tr>
                <th>Data</th>
                <th>Tipo</th>
                <th>Título</th>
                <th>Comentários</th>
                <th></th>
            </tr>
    """

    for registro in notas:
        body += f"""
            <tr>
                <td>{esc(registro["criado_em"][:10])}</td>
                <td>{esc(registro["tipo_registro"])}</td>

                <td>
                    <a class="link" href="/item/{registro["id"]}">
                        {esc(registro["titulo"])}
                    </a>
                </td>

                <td>{registro["comentarios"]}</td>

                <td class="actions">
                    <a class="link" href="/admin?editar={registro["id"]}">
                        Editar
                    </a>

                    <form
                        method="post"
                        action="/excluir/{registro["id"]}"
                        onsubmit="return confirm('Excluir este registro?')"
                    >
                        <button class="danger">Excluir</button>
                    </form>
                </td>
            </tr>
        """

    body += """
        </table>
        <h2>Moderação de comentários</h2>
    """

    for comentario in comentarios:
        contato = " · ".join(
            valor
            for valor in (
                esc(comentario["email"]),
                esc(comentario["telefone"]),
            )
            if valor
        ) or "Sem contato informado"

        body += f"""
            <div
                class="admin-comment"
                id="mod-{comentario["id"]}"
            >
                <strong>{esc(comentario["autor"]) or "Anônimo"}</strong>

                <small class="muted">
                    em
                    <a
                        class="admin-note"
                        href="/item/{comentario["nota_id"]}#comentario-{comentario["id"]}"
                    >
                        {esc(comentario["titulo"])}
                    </a>
                </small>

                <div class="comment-text">{esc(comentario["texto"])}</div>
                <div class="contact">{contato}</div>

                <form
                    method="post"
                    action="/admin/comentario/{comentario["id"]}/responder"
                >
                    <textarea
                        class="field"
                        name="texto"
                        rows="2"
                        maxlength="3000"
                        placeholder="Responder como administração..."
                        required
                    ></textarea>

                    <button>Responder</button>
                </form>

                <form
                    method="post"
                    action="/admin/comentario/{comentario["id"]}/excluir"
                    onsubmit="return confirm(
                        'Excluir este comentário e todas as respostas?'
                    )"
                >
                    <button class="danger">Excluir</button>
                </form>
            </div>
        """

    return pagina(body, "Administração")


@app.post("/admin/comentario/<int:id>/responder")
def admin_reply(id):
    resposta = admin_auth()
    if resposta:
        return resposta

    texto = request.form.get("texto", "").strip()[:3000]
    if not texto:
        abort(400)

    con = db()
    comentario = con.execute(
        "SELECT nota_id FROM comentarios WHERE id = ?",
        (id,),
    ).fetchone()

    if not comentario:
        con.close()
        abort(404)

    con.execute(
        """
        INSERT INTO comentarios (
            nota_id,
            parent_id,
            autor,
            texto
        )
        VALUES (?, ?, ?, ?)
        """,
        (comentario["nota_id"], id, "Administração", texto),
    )

    con.commit()
    con.close()

    return redirect(f"/admin#mod-{id}")


@app.post("/admin/comentario/<int:id>/excluir")
def admin_delete_comment(id):
    resposta = admin_auth()
    if resposta:
        return resposta

    con = db()

    if not con.execute(
        "SELECT 1 FROM comentarios WHERE id = ?",
        (id,),
    ).fetchone():
        con.close()
        abort(404)

    # Remove o comentário e todos os descendentes mesmo em bancos antigos
    # onde parent_id foi criado sem FOREIGN KEY.
    con.execute(
        """
        WITH RECURSIVE arvore(id) AS (
            SELECT id
            FROM comentarios
            WHERE id = ?

            UNION ALL

            SELECT c.id
            FROM comentarios AS c
            JOIN arvore AS a
                ON CAST(c.parent_id AS INTEGER) = a.id
        )
        DELETE FROM comentarios
        WHERE id IN (SELECT id FROM arvore)
        """,
        (id,),
    )

    con.commit()
    con.close()

    return redirect("/admin")


@app.post("/excluir/<int:id>")
def excluir(id):
    resposta = admin_auth()
    if resposta:
        return resposta

    con = db()

    con.execute(
        """
        DELETE FROM notas
        WHERE id = ?
        """,
        (id,),
    )

    con.commit()
    con.close()

    return redirect("/admin")


# ---------------------------------------------------------------------------
# Inicialização
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    con = db()
    con.close()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
    )
