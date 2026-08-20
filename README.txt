JasTech — versão pronta para Render.

ARQUIVOS
index.html          = site público
admin/index.html    = painel administrativo
server.py           = servidor + banco SQLite
render.yaml         = configuração automática do Render
requirements.txt    = dependências (nenhuma externa)

LOCAL
python server.py
Site: http://localhost:8000/
Admin: http://localhost:8000/admin/

RENDER
1. Coloque estes arquivos em um repositório GitHub.
2. No Render: New > Blueprint e selecione o repositório.
3. O render.yaml configura o Web Service automaticamente.
4. O endereço será parecido com: https://jastech-recrutamento.onrender.com
5. Admin: https://SEU-ENDERECO.onrender.com/admin/
6. Login inicial: usuário admin / senha 1234. Altere a senha dentro do painel, se essa opção existir na versão do projeto.

IMPORTANTE SOBRE OS DADOS
Esta versão usa SQLite. No plano Free do Render, o sistema de arquivos é efêmero; dados gravados no SQLite podem ser perdidos em reinícios/redeploys. Para dados de candidatos, empresas e vagas realmente permanentes, use um banco gerenciado (como PostgreSQL) ou um Persistent Disk compatível com o plano do Render e configure JASTECH_DATA_DIR para o diretório do disco.
