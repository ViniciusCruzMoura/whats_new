from flask import Flask, request, redirect, render_template_string
import sqlite3

app = Flask(__name__)
DB = "notas.db"

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("""
        CREATE TABLE IF NOT EXISTS notas_atualizacao(
            id INTEGER PRIMARY KEY,
            tipo_registro TEXT NOT NULL CHECK(tipo_registro IN('changelog','wishlist')),
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            tipo TEXT NOT NULL CHECK(tipo IN('novo','correcao','alteracao')),
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN('concluido','proposto','cancelado','em_andamento')),
            versao TEXT
        )
    """)
    return con

@app.get("/")
def index():
    con = db()
    notas = con.execute("SELECT * FROM notas_atualizacao ORDER BY criado_em DESC,status,tipo").fetchall()
    nota = con.execute("SELECT * FROM notas_atualizacao WHERE id=?", (request.args.get("editar"),)).fetchone() if request.args.get("editar") else None
    con.close()
    return render_template_string(ADMIN, notas=notas, nota=nota)

@app.get("/updates")
def updates():
    con = db()
    notas = con.execute("""
        SELECT * FROM notas_atualizacao
        ORDER BY tipo_registro='wishlist', criado_em DESC, tipo
    """).fetchall()
    con.close()
    return render_template_string(UPDATES, notas=notas)

@app.post("/salvar")
def salvar():
    dados = (
        request.form["tipo_registro"],
        request.form["tipo"],
        request.form["titulo"],
        request.form["descricao"],
        request.form["status"],
        request.form.get("versao") or None
    )
    con = db()
    if request.form.get("id"):
        con.execute("""
            UPDATE notas_atualizacao
            SET tipo_registro=?,tipo=?,titulo=?,descricao=?,status=?,versao=?
            WHERE id=?
        """, dados + (request.form["id"],))
    else:
        con.execute("""
            INSERT INTO notas_atualizacao
            (tipo_registro,tipo,titulo,descricao,status,versao)
            VALUES(?,?,?,?,?,?)
        """, dados)
    con.commit()
    con.close()
    return redirect("/")

@app.post("/excluir/<int:id>")
def excluir(id):
    con = db()
    con.execute("DELETE FROM notas_atualizacao WHERE id=?", (id,))
    con.commit()
    con.close()
    return redirect("/")

ADMIN = """
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 p-4 text-sm text-gray-900">
<main class="mx-auto max-w-6xl space-y-6">
<h1 class="text-2xl font-bold">Gerenciar atualizações</h1>
<a href="/updates" class="inline-block rounded bg-gray-800 px-4 py-2 text-white">Ver página pública</a>
<form method="post" action="/salvar" class="grid gap-3 rounded-lg bg-white p-4 shadow sm:grid-cols-2">
<input type="hidden" name="id" value="{{ nota.id if nota else '' }}">
<select name="tipo_registro" class="rounded border p-2" required>

{% for v,l in [('changelog','Changelog'),('wishlist','Wishlist')] %}
<option value="{{ v }}" {% if nota and nota.tipo_registro == v %}selected{% endif %}>{{ l }}</option>
{% endfor %}

</select>
<select name="tipo" class="rounded border p-2" required>

{% for v,l in [('novo','Novo'),('correcao','Correção'),('alteracao','Alteração')] %}
<option value="{{ v }}" {% if nota and nota.tipo == v %}selected{% endif %}>{{ l }}</option>
{% endfor %}

</select>
<input name="titulo" placeholder="Título" required value="{{ nota.titulo if nota else '' }}" class="rounded border p-2">
<input name="versao" placeholder="Versão" value="{{ nota.versao or '' if nota else '' }}" class="rounded border p-2">
<textarea name="descricao" placeholder="Descrição" required class="rounded border p-2 sm:col-span-2">{{ nota.descricao if nota else '' }}</textarea>
<select name="status" class="rounded border p-2" required>

{% for v,l in [('proposto','Proposto'),('em_andamento','Em andamento'),('concluido','Concluído'),('cancelado','Cancelado')] %}
<option value="{{ v }}" {% if nota and nota.status == v %}selected{% endif %}>{{ l }}</option>
{% endfor %}

</select>
<div class="flex gap-2">
<button class="rounded bg-blue-600 px-4 py-2 text-white">{{'Atualizar' if nota else 'Adicionar'}}</button>
{% if nota %}<a href="/" class="rounded bg-gray-300 px-4 py-2">Cancelar</a>{% endif %}
</div>
</form>
<div class="overflow-x-auto rounded-lg bg-white shadow">
<table class="w-full text-left">
<thead class="bg-gray-200"><tr>{% for h in ['Data','Registro','Tipo','Título','Descrição','Status','Versão','Ações'] %}<th class="p-3">{{h}}</th>{% endfor %}</tr></thead>
<tbody>
{% for n in notas %}
<tr class="border-t">
<td class="whitespace-nowrap p-3">{{n.criado_em}}</td><td class="p-3">{{n.tipo_registro}}</td><td class="p-3">{{n.tipo}}</td><td class="p-3 font-medium">{{n.titulo}}</td><td class="p-3">{{n.descricao}}</td><td class="p-3">{{n.status}}</td><td class="p-3">{{n.versao or '-'}}</td>
<td class="flex gap-2 p-3"><a href="/?editar={{n.id}}" class="text-blue-600">Editar</a><form method="post" action="/excluir/{{n.id}}"><button class="text-red-600" onclick="return confirm('Excluir esta nota?')">Excluir</button></form></td>
</tr>
{% else %}<tr><td colspan="8" class="p-6 text-center text-gray-500">Nenhuma nota cadastrada.</td></tr>{% endfor %}
</tbody>
</table>
</div>
</main>
</body>
</html>
"""

UPDATES = """
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-[#111318] text-white">
<header class="border-b border-white/10 bg-[#17191f]">
<div class="mx-auto flex max-w-5xl items-center justify-between px-6 py-5">
<h1 class="text-xl font-bold uppercase tracking-widest">Updates</h1>
<a href="/" class="text-sm text-gray-400 hover:text-white">Administração</a>
</div>
</header>

<main class="mx-auto max-w-5xl px-6 py-12">
<section class="mb-16">
<div class="mb-8 border-b border-white/10 pb-4">
<h2 class="text-3xl font-bold uppercase tracking-wide">Changelog</h2>
<p class="mt-2 text-gray-400">Latest changes and improvements.</p>
</div>

{% set ns = namespace(date='') %}
<div class="space-y-12">
{% for n in notas if n.tipo_registro == 'changelog' %}
{% set date = n.criado_em[:10] %}
{% if date != ns.date %}
{% set ns.date = date %}
<div>
<h3 class="mb-5 border-b border-white/10 pb-3 text-lg font-bold uppercase tracking-wider text-gray-300">
{{ date }}
</h3>
<div class="space-y-6">
{% endif %}

<article class="grid gap-5 border-b border-white/10 pb-6 md:grid-cols-[1fr_150px]">
<div>
<div class="mb-2 flex flex-wrap items-center gap-2">
<span class="rounded bg-blue-500/15 px-2 py-1 text-xs uppercase text-blue-400">{{ n.tipo }}</span>
<span class="rounded bg-white/10 px-2 py-1 text-xs uppercase text-gray-400">{{ n.status.replace('_',' ') }}</span>
</div>
<h4 class="text-xl font-semibold">{{ n.titulo }}</h4>
<p class="mt-2 whitespace-pre-line text-gray-400">{{ n.descricao }}</p>
</div>
<div class="text-sm text-gray-500">
{% if n.versao %}<span class="text-blue-400">{{ n.versao }}</span>{% endif %}
</div>
</article>

{% if loop.nextitem is not defined or loop.nextitem.criado_em[:10] != date %}
</div>
</div>
{% endif %}
{% else %}
<p class="text-gray-500">Nenhum changelog encontrado.</p>
{% endfor %}
</div>
</section>

<section>
<div class="mb-8 border-b border-white/10 pb-4">
<h2 class="text-3xl font-bold uppercase tracking-wide">Wishlist</h2>
<p class="mt-2 text-gray-400">Planned features and requested improvements.</p>
</div>

<div class="space-y-6">
{% for n in notas if n.tipo_registro == 'wishlist' %}
<article class="grid gap-5 border-b border-white/10 pb-6 md:grid-cols-[1fr_150px]">
<div>
<div class="mb-2 flex flex-wrap items-center gap-2">
<span class="rounded bg-purple-500/15 px-2 py-1 text-xs uppercase text-purple-400">{{ n.tipo }}</span>
<span class="rounded bg-white/10 px-2 py-1 text-xs uppercase text-gray-400">{{ n.status.replace('_',' ') }}</span>
</div>
<h3 class="text-xl font-semibold">{{ n.titulo }}</h3>
<p class="mt-2 whitespace-pre-line text-gray-400">{{ n.descricao }}</p>
</div>
<div class="text-sm text-gray-500">
{{ n.criado_em[:10] }}
{% if n.versao %}<div class="mt-2 text-blue-400">{{ n.versao }}</div>{% endif %}
</div>
</article>
{% else %}
<p class="text-gray-500">Nenhum item na wishlist.</p>
{% endfor %}
</div>
</section>
</main>
</body>
</html>
"""

UPDATES = """
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-[#111318] text-white">
<header class="border-b border-white/10 bg-[#17191f]">
<div class="mx-auto flex max-w-5xl items-center justify-between px-6 py-5">
<h1 class="text-xl font-bold uppercase tracking-widest">Updates</h1>
<a href="/" class="text-sm text-gray-400 hover:text-white">Administração</a>
</div>
</header>
<main class="mx-auto max-w-5xl px-6 py-12">
{% for grupo in ['changelog','wishlist'] %}
<section class="mb-16">
<div class="mb-8 border-b border-white/10 pb-4">
<h2 class="text-3xl font-bold uppercase tracking-wide">{{'Changelog' if grupo=='changelog' else 'Wishlist'}}</h2>
<p class="mt-2 text-gray-400">{{'Ultimas alterações e melhorias.' if grupo=='changelog' else 'Ideias and melhorias futuras.'}}</p>
</div>
<div class="space-y-6">
{% for n in notas if n.tipo_registro==grupo %}
<article class="grid gap-5 border-b border-white/10 pb-6 md:grid-cols-[150px_1fr]">
<div class="text-sm text-gray-500">{{n.criado_em[:10]}}{% if n.versao %}<div class="mt-2 text-xs uppercase text-blue-400">{{n.versao}}</div>{% endif %}</div>
<div>
<div class="mb-2 flex flex-wrap items-center gap-2">
<span class="rounded bg-blue-500/15 px-2 py-1 text-xs uppercase text-blue-400">{{n.tipo}}</span>
<span class="rounded bg-white/10 px-2 py-1 text-xs uppercase text-gray-400">{{n.status.replace('_',' ')}}</span>
</div>
<h3 class="text-xl font-semibold">{{n.titulo}}</h3>
<p class="mt-2 whitespace-pre-line text-gray-400">{{n.descricao}}</p>
</div>
</article>
{% else %}<p class="text-gray-500">Nenhum registro encontrado.</p>{% endfor %}
</div>
</section>
{% endfor %}
</main>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(debug=True)
