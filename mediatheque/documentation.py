import pydoc
import http.server
import socketserver

# Générer la documentation du module 'os' et l'afficher dans la console
doc = pydoc.render_doc('os', 'Help on %s')
print(doc)

# Créer un serveur HTTP local pour afficher la documentation
PORT = 8000  # Vous pouvez choisir un autre port si nécessaire
Handler = http.server.SimpleHTTPRequestHandler

# Créer un serveur qui écoute sur le port 8000
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serveur local en cours d'exécution sur http://localhost:{PORT}")
    httpd.serve_forever()
