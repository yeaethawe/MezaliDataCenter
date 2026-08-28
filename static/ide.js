(() => {
    const LANG_BY_EXT = {
        py: "python", pyw: "python", js: "javascript", jsx: "javascript", mjs: "javascript",
        cjs: "javascript", ts: "typescript", tsx: "typescript", html: "html", htm: "html",
        css: "css", scss: "scss", less: "less", json: "json", xml: "xml", yaml: "yaml",
        yml: "yaml", md: "markdown", markdown: "markdown", txt: "plaintext", csv: "plaintext",
        sql: "sql", sh: "shell", bash: "shell", zsh: "shell", ps1: "powershell", bat: "bat",
        cmd: "bat", c: "c", h: "c", cpp: "cpp", hpp: "cpp", cc: "cpp", cxx: "cpp", cs: "csharp",
        java: "java", kt: "kotlin", go: "go", rs: "rust", rb: "ruby", php: "php", swift: "swift",
        r: "r", lua: "lua", pl: "perl", vue: "html", svelte: "html", dart: "dart", scala: "scala",
        dockerfile: "dockerfile", makefile: "makefile", ini: "ini", toml: "ini", conf: "ini",
        cfg: "ini", env: "ini", gitignore: "ignore",
    };

    const openFileMeta = window.__IDE_OPEN_FILE__ || null;
    const treeEl = document.getElementById("ide-tree");
    const tabsEl = document.getElementById("ide-tabs");
    const emptyEl = document.getElementById("ide-empty");
    const editorHost = document.getElementById("monaco-editor");
    const previewHost = document.getElementById("ide-preview");
    const saveBtn = document.getElementById("ide-save");
    const statusFile = document.getElementById("status-file");
    const statusLang = document.getElementById("status-lang");
    const statusCursor = document.getElementById("status-cursor");
    const statusDirty = document.getElementById("status-dirty");
    const toastEl = document.getElementById("ide-toast");
    const sidebarEl = document.getElementById("ide-sidebar");
    const toggleSidebarBtn = document.getElementById("toggle-sidebar");
    const selectedPathEl = document.getElementById("ide-selected-path");

    const openTabs = new Map();
    let activeId = null;
    let editor = null;
    let monacoApi = null;
    let saving = false;
    let selectedFolderId = null;
    let selectedFolderName = "Root";
    let creating = false;
    let treeData = [];
    let clipboardItem = null;
    let ctxTarget = null;
    let moveTarget = null;

    function extOf(name) {
        const i = name.lastIndexOf(".");
        return i >= 0 ? name.slice(i + 1).toLowerCase() : "";
    }

    function languageFor(name) {
        return LANG_BY_EXT[extOf(name)] || "plaintext";
    }

    function modeLabel(mode) {
        if (mode === "edit") return null;
        if (mode === "image") return "Image";
        if (mode === "video") return "Video";
        if (mode === "audio") return "Audio";
        if (mode === "pdf") return "PDF";
        return "Preview";
    }

    function toast(message, isError = false) {
        toastEl.textContent = message;
        toastEl.classList.toggle("error", isError);
        toastEl.classList.add("show");
        clearTimeout(toastEl._timer);
        toastEl._timer = setTimeout(() => toastEl.classList.remove("show"), 2200);
    }

    function setSelectedFolder(folderId, folderName = "Root") {
        selectedFolderId = folderId;
        selectedFolderName = folderName || "Root";
        selectedPathEl.textContent = selectedFolderId == null ? "Creating in: Root" : `Creating in: ${selectedFolderName}`;
        document.querySelectorAll(".ide-tree-item.folder").forEach((node) => {
            node.classList.toggle("selected", Number(node.dataset.folderId) === selectedFolderId);
        });
    }

    function showWorkspace(mode) {
        const hasTabs = openTabs.size > 0;
        emptyEl.style.display = hasTabs ? "none" : "grid";
        if (!hasTabs) {
            editorHost.style.display = "none";
            previewHost.style.display = "none";
            previewHost.replaceChildren();
            return;
        }
        const isEdit = mode === "edit";
        editorHost.style.display = isEdit ? "block" : "none";
        previewHost.style.display = isEdit ? "none" : "grid";
    }

    function renderPreview(tab) {
        previewHost.replaceChildren();
        if (tab.mode === "image") {
            const image = document.createElement("img");
            image.src = tab.previewUrl;
            image.alt = tab.name;
            previewHost.appendChild(image);
            return;
        }
        if (tab.mode === "video") {
            const video = document.createElement("video");
            video.src = tab.previewUrl;
            video.controls = true;
            video.playsInline = true;
            previewHost.appendChild(video);
            return;
        }
        if (tab.mode === "audio") {
            const audio = document.createElement("audio");
            audio.src = tab.previewUrl;
            audio.controls = true;
            previewHost.appendChild(audio);
            return;
        }
        if (tab.mode === "pdf") {
            const frame = document.createElement("iframe");
            frame.src = tab.previewUrl;
            frame.title = tab.name;
            previewHost.appendChild(frame);
            return;
        }
        const box = document.createElement("div");
        box.className = "ide-preview-empty";
        const title = document.createElement("h2");
        title.textContent = tab.name;
        const note = document.createElement("p");
        note.textContent = "No in-IDE preview for this file type. Download it to open with another app.";
        const link = document.createElement("a");
        link.href = tab.downloadUrl || tab.previewUrl;
        link.textContent = "Download file";
        box.append(title, note, link);
        previewHost.appendChild(box);
    }

    function updateStatus() {
        const tab = activeId != null ? openTabs.get(activeId) : null;
        statusFile.textContent = tab ? tab.name : "No file open";
        if (!tab) {
            statusLang.textContent = "—";
            statusDirty.textContent = "Saved";
            statusCursor.textContent = "Ln —, Col —";
            saveBtn.disabled = true;
            return;
        }
        if (tab.mode === "edit") {
            statusLang.textContent = languageFor(tab.name);
            statusDirty.textContent = tab.dirty ? "Modified" : "Saved";
            saveBtn.disabled = !tab.dirty || saving;
            if (editor) {
                const pos = editor.getPosition();
                statusCursor.textContent = pos ? `Ln ${pos.lineNumber}, Col ${pos.column}` : "Ln —, Col —";
            }
        } else {
            statusLang.textContent = modeLabel(tab.mode) || tab.mime || "File";
            statusDirty.textContent = "Preview";
            statusCursor.textContent = "—";
            saveBtn.disabled = true;
        }
    }

    function renderTabs() {
        tabsEl.replaceChildren();
        for (const [id, tab] of openTabs) {
            const el = document.createElement("div");
            el.className = `ide-tab${id === activeId ? " active" : ""}${tab.dirty ? " dirty" : ""}`;
            el.dataset.id = String(id);
            el.title = tab.name;
            const label = document.createElement("span");
            label.textContent = tab.name;
            const close = document.createElement("button");
            close.type = "button";
            close.className = "ide-tab-close";
            close.setAttribute("aria-label", `Close ${tab.name}`);
            close.textContent = "×";
            close.addEventListener("click", (event) => {
                event.stopPropagation();
                closeTab(id);
            });
            el.append(label, close);
            el.addEventListener("click", () => activateTab(id));
            tabsEl.appendChild(el);
        }
        const tab = activeId != null ? openTabs.get(activeId) : null;
        showWorkspace(tab ? tab.mode : null);
        updateStatus();
    }

    function markDirty(id, dirty) {
        const tab = openTabs.get(id);
        if (!tab || tab.mode !== "edit" || tab.dirty === dirty) {
            if (tab) updateStatus();
            return;
        }
        tab.dirty = dirty;
        renderTabs();
    }

    async function activateTab(id) {
        if (!openTabs.has(id)) return;
        activeId = id;
        const tab = openTabs.get(id);
        history.replaceState(null, "", `/ide/${id}`);
        document.querySelectorAll(".ide-tree-item.file").forEach((node) => {
            node.classList.toggle("active", Number(node.dataset.fileId) === id);
        });
        if (tab.mode === "edit") {
            if (!editor || !tab.model) return;
            monacoApi.editor.setModelLanguage(tab.model, languageFor(tab.name));
            editor.setModel(tab.model);
            editor.focus();
            previewHost.replaceChildren();
        } else {
            if (editor) editor.setModel(null);
            renderPreview(tab);
        }
        renderTabs();
        if (window.innerWidth <= 900) sidebarEl.classList.remove("open");
    }

    async function closeTab(id) {
        const tab = openTabs.get(id);
        if (!tab) return;
        if (tab.dirty && !window.confirm(`"${tab.name}" has unsaved changes. Close anyway?`)) return;
        if (tab.model) tab.model.dispose();
        openTabs.delete(id);
        if (activeId === id) {
            const next = openTabs.keys().next().value;
            activeId = next ?? null;
            if (activeId != null) {
                await activateTab(activeId);
            } else {
                if (editor) editor.setModel(null);
                previewHost.replaceChildren();
                history.replaceState(null, "", "/ide");
                renderTabs();
            }
        } else {
            renderTabs();
        }
    }

    async function openFile(id) {
        if (openTabs.has(id)) {
            await activateTab(id);
            return;
        }
        const response = await fetch(`/api/ide/files/${id}`);
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            toast(data.error || "Could not open file.", true);
            return;
        }
        const tab = {
            id: data.id,
            name: data.name,
            mime: data.mime,
            mode: data.mode || "none",
            dirty: false,
            previewUrl: data.preview_url,
            downloadUrl: data.download_url,
            model: null,
            savingBaseline: "",
        };
        if (tab.mode === "edit") {
            tab.model = monacoApi.editor.createModel(data.content || "", languageFor(data.name));
            tab.savingBaseline = data.content || "";
            tab.model.onDidChangeContent(() => {
                markDirty(data.id, tab.model.getValue() !== tab.savingBaseline);
            });
        }
        openTabs.set(data.id, tab);
        await activateTab(data.id);
    }

    async function saveActive() {
        if (activeId == null || !openTabs.has(activeId) || saving) return;
        const tab = openTabs.get(activeId);
        if (tab.mode !== "edit" || !tab.dirty || !tab.model) return;
        saving = true;
        updateStatus();
        try {
            const response = await fetch(`/api/ide/files/${tab.id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ content: tab.model.getValue() }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                toast(data.error || "Save failed.", true);
                return;
            }
            tab.savingBaseline = tab.model.getValue();
            markDirty(tab.id, false);
            toast(`Saved ${tab.name}`);
        } catch (_) {
            toast("Save failed.", true);
        } finally {
            saving = false;
            updateStatus();
        }
    }

    function renderTree(nodes, depth = 0, parentFolderId = null) {
        const frag = document.createDocumentFragment();
        for (const node of nodes) {
            const row = document.createElement("div");
            row.className = `ide-tree-item ${node.type}`;
            row.style.setProperty("--depth", String(depth));
            row.draggable = true;
            row.dataset.nodeType = node.type;
            row.dataset.nodeId = String(node.id);
            row.dataset.nodeName = node.name;
            row.dataset.parentFolderId = parentFolderId == null ? "" : String(parentFolderId);
            if (node.mime) row.dataset.nodeMime = node.mime;
            if (node.size != null) row.dataset.nodeSize = String(node.size);
            const icon = document.createElement("i");
            if (node.type === "folder") {
                icon.className = "bi bi-folder-fill";
                if (selectedFolderId === node.id) row.classList.add("selected");
            } else {
                icon.className = `bi ${node.icon || "bi-file-earmark-code"} ${node.color || ""}`.trim();
            }
            const label = document.createElement("span");
            label.textContent = node.name;
            row.append(icon, label);

            row.addEventListener("dragstart", (event) => {
                event.stopPropagation();
                row.classList.add("dragging");
                row.dataset.didDrag = "1";
                const payload = node.type === "folder"
                    ? { type: "folder", id: node.id, name: node.name }
                    : { type: "file", id: node.id, name: node.name };
                event.dataTransfer.setData("application/x-ide-item", JSON.stringify(payload));
                event.dataTransfer.setData("text/plain", node.name);
                event.dataTransfer.effectAllowed = "move";
            });
            row.addEventListener("dragend", () => {
                row.classList.remove("dragging");
                clearDragOver();
                setTimeout(() => { delete row.dataset.didDrag; }, 0);
            });

            if (node.type === "folder") {
                row.dataset.folderId = String(node.id);
                let expanded = false;
                const childrenHost = document.createElement("div");
                childrenHost.className = "ide-tree-children";
                childrenHost.dataset.parentFolderId = String(node.id);
                childrenHost.style.display = "none";
                icon.className = "bi bi-folder";
                if (node.children?.length) {
                    childrenHost.appendChild(renderTree(node.children, depth + 1, node.id));
                }
                bindDropTarget(row, node.id, node.name);
                row.addEventListener("click", (event) => {
                    event.stopPropagation();
                    if (row.dataset.didDrag === "1") return;
                    setSelectedFolder(node.id, node.name);
                    expanded = !expanded;
                    childrenHost.style.display = expanded ? "" : "none";
                    icon.className = expanded ? "bi bi-folder-fill" : "bi bi-folder";
                });
                frag.append(row, childrenHost);
            } else {
                row.dataset.fileId = String(node.id);
                row.addEventListener("click", (event) => {
                    event.stopPropagation();
                    if (row.dataset.didDrag === "1") return;
                    openFile(node.id);
                });
                frag.appendChild(row);
            }
        }
        return frag;
    }

    function clearDragOver() {
        document.querySelectorAll(".drag-over").forEach((el) => el.classList.remove("drag-over"));
    }

    function parseDragPayload(event) {
        try {
            return JSON.parse(event.dataTransfer.getData("application/x-ide-item") || "null");
        } catch (_) {
            return null;
        }
    }

    function bindDropTarget(element, folderId, folderName = "Root") {
        element.addEventListener("dragover", (event) => {
            const types = event.dataTransfer.types;
            if (![...types].includes("application/x-ide-item") && ![...types].includes("text/plain")) return;
            event.preventDefault();
            event.stopPropagation();
            event.dataTransfer.dropEffect = "move";
            clearDragOver();
            element.classList.add("drag-over");
        });
        element.addEventListener("dragleave", (event) => {
            if (!element.contains(event.relatedTarget)) element.classList.remove("drag-over");
        });
        element.addEventListener("drop", async (event) => {
            event.preventDefault();
            event.stopPropagation();
            clearDragOver();
            const payload = parseDragPayload(event);
            if (!payload) return;
            if (payload.type === "folder" && folderId != null && payload.id === folderId) {
                toast("Cannot move a folder into itself.", true);
                return;
            }
            await moveItem(payload, folderId, folderName);
        });
    }

    async function moveItem(payload, targetFolderId, targetName = "Root") {
        const endpoint = payload.type === "folder"
            ? `/api/ide/folders/${payload.id}/move`
            : `/api/ide/files/${payload.id}/move`;
        try {
            const response = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ folder_id: targetFolderId }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                toast(data.error || "Could not move item.", true);
                return;
            }
            toast(`Moved ${payload.name} to ${targetName}`);
            if (payload.type === "folder" && selectedFolderId === payload.id) {
                selectedFolderName = payload.name;
            }
            await loadTree();
        } catch (_) {
            toast("Could not move item.", true);
        }
    }

    async function loadTree() {
        const response = await fetch("/api/ide/tree");
        const data = await response.json().catch(() => ({ tree: [] }));
        treeData = data.tree || [];
        treeEl.replaceChildren();
        if (!treeData.length) {
            const empty = document.createElement("div");
            empty.className = "ide-tree-empty";
            empty.textContent = "No files yet. Use + to create a file or folder.";
            treeEl.appendChild(empty);
        } else {
            treeEl.appendChild(renderTree(treeData));
        }
        setSelectedFolder(selectedFolderId, selectedFolderName);
    }

    function cancelCreateRow() {
        treeEl.querySelector(".ide-create-row")?.remove();
        creating = false;
    }

    function startCreate(kind) {
        if (creating) cancelCreateRow();
        creating = true;
        const row = document.createElement("div");
        row.className = "ide-create-row";
        row.style.setProperty("--depth", selectedFolderId == null ? "0" : "1");
        const icon = document.createElement("i");
        icon.className = kind === "folder" ? "bi bi-folder" : "bi bi-file-earmark";
        const input = document.createElement("input");
        input.type = "text";
        input.maxLength = 120;
        input.placeholder = kind === "folder" ? "New folder" : "untitled.py";
        input.value = kind === "folder" ? "New folder" : "untitled.py";
        input.setAttribute("aria-label", kind === "folder" ? "New folder name" : "New file name");
        row.append(icon, input);

        const mount = () => {
            if (selectedFolderId == null) {
                const empty = treeEl.querySelector(".ide-tree-empty");
                if (empty) empty.remove();
                treeEl.prepend(row);
            } else {
                const childrenHost = treeEl.querySelector(`.ide-tree-children[data-parent-folder-id="${selectedFolderId}"]`);
                if (childrenHost) {
                    childrenHost.style.display = "";
                    const folderRow = treeEl.querySelector(`.ide-tree-item.folder[data-folder-id="${selectedFolderId}"]`);
                    const folderIcon = folderRow?.querySelector("i");
                    if (folderIcon) folderIcon.className = "bi bi-folder-fill";
                    childrenHost.prepend(row);
                } else {
                    treeEl.prepend(row);
                }
            }
            input.focus();
            input.select();
        };

        const submit = async () => {
            const name = input.value.trim();
            if (!name) {
                cancelCreateRow();
                return;
            }
            input.disabled = true;
            const endpoint = kind === "folder" ? "/api/ide/folders" : "/api/ide/files";
            try {
                const response = await fetch(endpoint, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name, folder_id: selectedFolderId }),
                });
                const data = await response.json().catch(() => ({}));
                if (!response.ok) {
                    toast(data.error || "Could not create.", true);
                    input.disabled = false;
                    input.focus();
                    return;
                }
                creating = false;
                toast(kind === "folder" ? `Created folder ${data.name}` : `Created ${data.name}`);
                if (kind === "folder") {
                    selectedFolderId = data.id;
                    selectedFolderName = data.name;
                }
                await loadTree();
                if (kind === "file" && data.id) await openFile(data.id);
            } catch (_) {
                toast("Could not create.", true);
                input.disabled = false;
            }
        };

        input.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                submit();
            } else if (event.key === "Escape") {
                event.preventDefault();
                cancelCreateRow();
            }
        });
        input.addEventListener("blur", () => {
            setTimeout(() => {
                if (creating && document.activeElement !== input) {
                    if (input.value.trim()) submit();
                    else cancelCreateRow();
                }
            }, 120);
        });

        mount();
    }

    function initMonaco() {
        return new Promise((resolve) => {
            require.config({
                paths: { vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs" },
            });
            window.MonacoEnvironment = {
                getWorkerUrl() {
                    return URL.createObjectURL(new Blob([
                        "self.MonacoEnvironment={baseUrl:'https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/'};",
                        "importScripts('https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs/base/worker/workerMain.js');",
                    ], { type: "text/javascript" }));
                },
            };
            require(["vs/editor/editor.main"], () => {
                monacoApi = window.monaco;
                editor = monacoApi.editor.create(editorHost, {
                    value: "",
                    language: "plaintext",
                    theme: "vs-dark",
                    automaticLayout: true,
                    fontSize: 14,
                    fontFamily: "Consolas, 'Courier New', monospace",
                    minimap: { enabled: true },
                    scrollBeyondLastLine: false,
                    renderWhitespace: "selection",
                    tabSize: 4,
                    insertSpaces: true,
                    wordWrap: "off",
                    padding: { top: 8 },
                });
                editor.onDidChangeCursorPosition(updateStatus);
                editor.addCommand(monacoApi.KeyMod.CtrlCmd | monacoApi.KeyCode.KeyS, () => {
                    saveActive();
                });
                resolve();
            });
        });
    }

    saveBtn.addEventListener("click", saveActive);
    document.getElementById("ide-refresh-tree").addEventListener("click", loadTree);
    document.getElementById("ide-new-file").addEventListener("click", () => startCreate("file"));
    document.getElementById("ide-new-folder").addEventListener("click", () => startCreate("folder"));
    const dropRootEl = document.getElementById("ide-drop-root");
    bindDropTarget(dropRootEl, null, "Root");
    dropRootEl.addEventListener("click", () => setSelectedFolder(null, "Root"));
    treeEl.addEventListener("click", (event) => {
        if (event.target === treeEl || event.target.classList.contains("ide-tree-empty")) {
            setSelectedFolder(null, "Root");
        }
    });

    const ctxMenu = document.getElementById("ide-context-menu");
    const detailModal = document.getElementById("ide-detail-modal");
    const moveModal = document.getElementById("ide-move-modal");
    const moveSelect = document.getElementById("ide-move-select");
    const detailBody = document.getElementById("ide-detail-body");

    function formatBytes(bytes) {
        const value = Number(bytes) || 0;
        if (value >= 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} MB`;
        if (value >= 1024) return `${Math.max(1, Math.round(value / 1024))} KB`;
        return `${value} B`;
    }

    function formatStamp(iso) {
        if (!iso) return "—";
        return String(iso).replace("T", " ").slice(0, 19);
    }

    function hideCtxMenu() {
        ctxMenu.classList.remove("is-open");
        ctxMenu.setAttribute("aria-hidden", "true");
        document.querySelectorAll(".ide-tree-item.ctx-target").forEach((el) => el.classList.remove("ctx-target"));
        ctxTarget = null;
    }

    function openModal(el) {
        el.classList.add("is-open");
        el.setAttribute("aria-hidden", "false");
    }

    function closeModal(el) {
        el.classList.remove("is-open");
        el.setAttribute("aria-hidden", "true");
    }

    function flattenFolders(nodes, prefix = "", out = [{ id: null, label: "/Root" }]) {
        for (const node of nodes) {
            if (node.type !== "folder") continue;
            const label = `${prefix}/${node.name}`;
            out.push({ id: node.id, label });
            if (node.children?.length) flattenFolders(node.children, label, out);
        }
        return out;
    }

    function payloadFromRow(row) {
        if (!row) return null;
        return {
            type: row.dataset.nodeType,
            id: Number(row.dataset.nodeId),
            name: row.dataset.nodeName,
        };
    }

    function openCtxMenu(event, row) {
        event.preventDefault();
        event.stopPropagation();
        hideCtxMenu();
        ctxTarget = row;
        row.classList.add("ctx-target");
        const pasteBtn = ctxMenu.querySelector('[data-ide-ctx="paste"]');
        pasteBtn.disabled = !clipboardItem;
        pasteBtn.textContent = "";
        pasteBtn.innerHTML = `<i class="bi bi-clipboard-check" aria-hidden="true"></i> Paste${clipboardItem ? ` (${clipboardItem.name})` : ""}`;
        ctxMenu.classList.add("is-open");
        ctxMenu.setAttribute("aria-hidden", "false");
        const pad = 8;
        const rect = ctxMenu.getBoundingClientRect();
        let left = event.clientX;
        let top = event.clientY;
        if (left + rect.width > window.innerWidth - pad) left = window.innerWidth - rect.width - pad;
        if (top + rect.height > window.innerHeight - pad) top = window.innerHeight - rect.height - pad;
        ctxMenu.style.left = `${Math.max(pad, left)}px`;
        ctxMenu.style.top = `${Math.max(pad, top)}px`;
    }

    async function showDetail(payload) {
        const endpoint = payload.type === "folder"
            ? `/api/ide/folders/${payload.id}/detail`
            : `/api/ide/files/${payload.id}/detail`;
        try {
            const response = await fetch(endpoint);
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                toast(data.error || "Could not load details.", true);
                return;
            }
            detailBody.replaceChildren();
            const rows = payload.type === "folder"
                ? [
                    ["Name", data.name],
                    ["Type", "Folder"],
                    ["Path", data.path || "—"],
                    ["Files", String(data.files ?? 0)],
                    ["Subfolders", String(data.folders ?? 0)],
                    ["Created", formatStamp(data.created_at)],
                ]
                : [
                    ["Name", data.name],
                    ["Type", "File"],
                    ["Path", data.path || "—"],
                    ["MIME", data.mime || "—"],
                    ["Size", formatBytes(data.size)],
                    ["Mode", data.mode || "—"],
                    ["Created", formatStamp(data.created_at)],
                ];
            for (const [key, value] of rows) {
                const dt = document.createElement("dt");
                dt.textContent = key;
                const dd = document.createElement("dd");
                dd.textContent = value;
                detailBody.append(dt, dd);
            }
            openModal(detailModal);
        } catch (_) {
            toast("Could not load details.", true);
        }
    }

    async function deleteTarget(payload) {
        const label = payload.type === "folder" ? "folder" : "file";
        if (!confirm(`Delete ${label} "${payload.name}"?`)) return;
        const endpoint = payload.type === "folder"
            ? `/api/ide/folders/${payload.id}`
            : `/api/ide/files/${payload.id}`;
        try {
            const response = await fetch(endpoint, { method: "DELETE" });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                toast(data.error || "Could not delete.", true);
                return;
            }
            if (payload.type === "file" && openTabs.has(payload.id)) closeTab(payload.id);
            if (payload.type === "folder" && selectedFolderId === payload.id) {
                setSelectedFolder(null, "Root");
            }
            toast(`Deleted ${payload.name}`);
            await loadTree();
        } catch (_) {
            toast("Could not delete.", true);
        }
    }

    function openMoveDialog(payload) {
        moveTarget = payload;
        const options = flattenFolders(treeData).filter((folder) => {
            if (payload.type === "folder" && folder.id === payload.id) return false;
            return true;
        });
        moveSelect.replaceChildren();
        for (const folder of options) {
            const option = document.createElement("option");
            option.value = folder.id == null ? "" : String(folder.id);
            option.textContent = folder.label;
            moveSelect.appendChild(option);
        }
        openModal(moveModal);
    }

    async function pasteInto(targetFolderId, targetName = "destination") {
        if (!clipboardItem) {
            toast("Clipboard is empty.", true);
            return;
        }
        const endpoint = clipboardItem.type === "folder"
            ? `/api/ide/folders/${clipboardItem.id}/copy`
            : `/api/ide/files/${clipboardItem.id}/copy`;
        try {
            const response = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ folder_id: targetFolderId }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                toast(data.error || "Could not paste.", true);
                return;
            }
            toast(`Pasted ${clipboardItem.name} into ${targetName}`);
            await loadTree();
        } catch (_) {
            toast("Could not paste.", true);
        }
    }

    treeEl.addEventListener("contextmenu", (event) => {
        const row = event.target.closest(".ide-tree-item");
        if (!row || !treeEl.contains(row)) return;
        openCtxMenu(event, row);
    });

    document.getElementById("ide-drop-root").addEventListener("contextmenu", (event) => {
        event.preventDefault();
        hideCtxMenu();
        if (!clipboardItem) {
            toast("Copy a file or folder first to paste into Root.", true);
            return;
        }
        pasteInto(null, "Root");
    });

    document.addEventListener("click", (event) => {
        if (!ctxMenu.contains(event.target)) hideCtxMenu();
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            hideCtxMenu();
            closeModal(detailModal);
            closeModal(moveModal);
        }
    });
    window.addEventListener("scroll", hideCtxMenu, true);

    ctxMenu.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-ide-ctx]");
        if (!button || !ctxTarget) return;
        const action = button.dataset.ideCtx;
        const payload = payloadFromRow(ctxTarget);
        const parentFolderRaw = ctxTarget?.dataset.parentFolderId;
        hideCtxMenu();
        if (!payload) return;
        if (action === "copy") {
            clipboardItem = payload;
            toast(`Copied ${payload.name}`);
            return;
        }
        if (action === "paste") {
            let destId = selectedFolderId;
            let destName = selectedFolderName;
            if (payload.type === "folder") {
                destId = payload.id;
                destName = payload.name;
            } else if (parentFolderRaw !== undefined) {
                destId = parentFolderRaw === "" ? null : Number(parentFolderRaw);
                destName = destId == null ? "Root" : "folder";
            }
            await pasteInto(destId, destName);
            return;
        }
        if (action === "move") {
            openMoveDialog(payload);
            return;
        }
        if (action === "detail") {
            await showDetail(payload);
            return;
        }
        if (action === "delete") {
            await deleteTarget(payload);
        }
    });

    document.querySelectorAll("[data-ide-close]").forEach((btn) => {
        btn.addEventListener("click", () => {
            const id = btn.getAttribute("data-ide-close");
            closeModal(document.getElementById(id));
        });
    });
    detailModal.addEventListener("click", (event) => {
        if (event.target === detailModal) closeModal(detailModal);
    });
    moveModal.addEventListener("click", (event) => {
        if (event.target === moveModal) closeModal(moveModal);
    });
    document.getElementById("ide-move-confirm").addEventListener("click", async () => {
        if (!moveTarget) return;
        const raw = moveSelect.value;
        const folderId = raw === "" ? null : Number(raw);
        const label = moveSelect.selectedOptions[0]?.textContent || "destination";
        closeModal(moveModal);
        await moveItem(moveTarget, folderId, label);
        moveTarget = null;
    });

    toggleSidebarBtn.addEventListener("click", () => {
        sidebarEl.classList.toggle("open");
        toggleSidebarBtn.classList.toggle("active");
    });
    window.addEventListener("beforeunload", (event) => {
        for (const tab of openTabs.values()) {
            if (tab.dirty) {
                event.preventDefault();
                event.returnValue = "";
                return;
            }
        }
    });

    setSelectedFolder(null, "Root");

    (async () => {
        await initMonaco();
        await loadTree();
        if (openFileMeta?.id) await openFile(openFileMeta.id);
        updateStatus();
    })();
})();
