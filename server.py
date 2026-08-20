import os
from flask import Flask, send_from_directory

app = Flask(__name__, static_folder='.')

# 1. Entrega o SITE PÚBLICO na página inicial (/)
@app.route('/')
def public_site():
    return send_from_directory('.', 'index.html')

# 2. Entrega o PAINEL ADMIN apenas na rota (/admin)
@app.route('/admin')
@app.route('/admin/')
@app.route('/admin/<path:path>')
def admin_site(path='index.html'):
    if os.path.exists(os.path.join('admin', path)):
        return send_from_directory('admin', path)
    return send_from_directory('.', 'index.html')

# 3. Entrega arquivos estáticos (CSS, imagens, JS)
@app.route('/<path:path>')
def static_files(path):
    if os.path.exists(path):
        return send_from_directory('.', path)
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
