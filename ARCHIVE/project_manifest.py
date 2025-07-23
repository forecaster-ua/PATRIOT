import zipfile
import ast
import json
import re
import os

# Путь к архиву проекта
zip_path = '!PATRIOT.zip'

# Файлы, которые считаем защищёнными (не менять)
protected_files = {'config.py', 'utils.py', 'database.py', 'api_client.py'}

# Считываем внешние зависимости из requirements.txt, если они есть
external_dependencies = []
with zipfile.ZipFile(zip_path, 'r') as z:
    req_files = [f for f in z.namelist() if f.endswith('requirements.txt')]
    if req_files:
        req_txt = z.read(req_files[0]).decode('utf-8', errors='ignore')
        external_dependencies = [
            line.strip() for line in req_txt.splitlines()
            if line.strip() and not line.strip().startswith('#')
        ]

manifest = {
    "project": {
        "name": os.path.splitext(os.path.basename(zip_path))[0].lstrip('!'),
        "description": "Сервис автоматической торговли на основе сигналов из Telegram."
    },
    "external_dependencies": external_dependencies,
    "files": {}
}

# Обрабатываем файлы внутри архива
with zipfile.ZipFile(zip_path, 'r') as z:
    entries = z.namelist()
    # Определяем корневую папку проекта внутри архива
    roots = {e.split('/', 1)[0] for e in entries if '/' in e}
    root = roots.pop() if roots else ''

    for entry in entries:
        # Пропускаем не-основные элементы
        if not entry.startswith(root + '/') or entry.endswith('/') or '__pycache__' in entry:
            continue
        fname = entry[len(root) + 1:]
        if fname.lower() == 'manifest.json':
            continue

        record = {"protected": fname in protected_files}
        content = z.read(entry)

        if fname.endswith('.py'):
            text = content.decode('utf-8', errors='ignore')
            tree = ast.parse(text)
            # Докстринг модуля
            record["description"] = ast.get_docstring(tree) or ""

            # Сбор функций и классов
            definitions = []
            for node in tree.body:
                if isinstance(node, ast.FunctionDef):
                    sig = f"def {node.name}({', '.join(arg.arg for arg in node.args.args)})"
                    doc = ast.get_docstring(node) or ""
                    definitions.append({"type": "function", "name": node.name, "signature": sig, "doc": doc})
                elif isinstance(node, ast.ClassDef):
                    # Базовые классы
                    bases = []
                    for base in node.bases:
                        try:
                            bases.append(ast.unparse(base))
                        except Exception:
                            bases.append(getattr(base, 'id', ''))
                    sig = f"class {node.name}({', '.join(bases)})"
                    doc = ast.get_docstring(node) or ""
                    methods = []
                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            args = [arg.arg for arg in child.args.args[1:]]
                            msig = f"def {child.name}(self{', ' + ', '.join(args) if args else ''})"
                            mdoc = ast.get_docstring(child) or ""
                            methods.append({"name": child.name, "signature": msig, "doc": mdoc})
                    definitions.append({"type": "class", "name": node.name, "signature": sig, "doc": doc, "methods": methods})

            # Поиск импортов и зависимостей
            imports = re.findall(r'^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w_]+))', text, re.MULTILINE)
            imported = [imp for grp in imports for imp in grp if imp]
            project_modules = {os.path.splitext(os.path.basename(f))[0]
                               for f in entries if f.startswith(root + '/') and f.endswith('.py')}
            deps = [imp for imp in imported if imp in project_modules]

            record.update({
                "type": "module",
                "definitions": definitions,
                "dependencies": deps
            })
        else:
            # Ресурсные файлы
            ext = os.path.splitext(fname)[1].lstrip('.')
            record.update({
                "type": "resource",
                "description": f"Resource file of type .{ext}",
                "dependencies": []
            })

        manifest["files"][fname] = record

# Сохраняем финальный манифест в JSON
output_path = 'project_manifest.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)
print(f"Updated manifest saved to {output_path}")
