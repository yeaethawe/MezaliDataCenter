(function () {
    const EMOJI_CATEGORIES = [
        {
            id: "recent",
            label: "Recent",
            icon: "bi-clock-history",
            emojis: [],
        },
        {
            id: "people",
            label: "Emoji & People",
            icon: "bi-emoji-smile",
            emojis: [
                "😀", "😁", "😂", "🤣", "😃", "😄", "😅", "😆", "😉", "😊", "😋", "😎", "😍", "😘", "😗", "😙",
                "😚", "🙂", "🤗", "🤩", "🤔", "🤨", "😐", "😑", "😶", "🙄", "😏", "😣", "😥", "😮", "🤐", "😯",
                "😪", "😫", "🥱", "😴", "😌", "😛", "😜", "😝", "🤤", "😒", "😓", "😔", "😕", "🙃", "🤑", "😲",
                "☹️", "🙁", "😖", "😞", "😟", "😤", "😢", "😭", "😦", "😧", "😨", "😩", "🤯", "😬", "😰", "😱",
                "🥵", "🥶", "😳", "🤪", "😵", "😡", "😠", "🤬", "😷", "🤒", "🤕", "🤢", "🤮", "🤧", "😇", "🥳",
                "🥺", "🤠", "🤡", "🤥", "🤫", "🤭", "🧐", "🤓", "😈", "👿", "👹", "👺", "💀", "👻", "👽", "🤖",
                "💩", "😺", "😸", "😹", "😻", "😼", "😽", "🙀", "😿", "😾", "👋", "🤚", "🖐", "✋", "🖖", "👌",
                "🤌", "🤏", "✌️", "🤞", "🤟", "🤘", "🤙", "👈", "👉", "👆", "🖕", "👇", "☝️", "👍", "👎", "✊",
                "👊", "🤛", "🤜", "👏", "🙌", "👐", "🤲", "🤝", "🙏", "✍️", "💅", "🤳", "💪", "🦾", "🦵", "🦶",
            ],
        },
        {
            id: "nature",
            label: "Animals & Nature",
            icon: "bi-flower1",
            emojis: [
                "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯", "🦁", "🐮", "🐷", "🐸", "🐵", "🙈",
                "🙉", "🙊", "🐒", "🐔", "🐧", "🐦", "🐤", "🐣", "🐥", "🦆", "🦅", "🦉", "🦇", "🐺", "🐗", "🐴",
                "🦄", "🐝", "🐛", "🦋", "🐌", "🐞", "🐜", "🦟", "🦗", "🕷", "🦂", "🐢", "🐍", "🦎", "🦖", "🦕",
                "🐙", "🦑", "🦐", "🦞", "🦀", "🐡", "🐠", "🐟", "🐬", "🐳", "🐋", "🦈", "🐊", "🐅", "🐆", "🦓",
                "🦍", "🦧", "🐘", "🦛", "🦏", "🐪", "🐫", "🦒", "🦘", "🦬", "🐃", "🐂", "🐄", "🐎", "🐖", "🐏",
                "🌸", "💮", "🏵", "🌹", "🥀", "🌺", "🌻", "🌼", "🌷", "🌱", "🪴", "🌲", "🌳", "🌴", "🌵", "🌾",
            ],
        },
        {
            id: "food",
            label: "Food & Drink",
            icon: "bi-cup-straw",
            emojis: [
                "🍎", "🍐", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🫐", "🍈", "🍒", "🍑", "🥭", "🍍", "🥥", "🥝",
                "🍅", "🍆", "🥑", "🥦", "🥬", "🥒", "🌶", "🫑", "🌽", "🥕", "🫒", "🧄", "🧅", "🥔", "🍠", "🥐",
                "🥯", "🍞", "🥖", "🥨", "🧀", "🥚", "🍳", "🧈", "🥞", "🧇", "🥓", "🥩", "🍗", "🍖", "🦴", "🌭",
                "🍔", "🍟", "🍕", "🫓", "🥪", "🥙", "🧆", "🌮", "🌯", "🫔", "🥗", "🥘", "🫕", "🥫", "🍝", "🍜",
                "🍲", "🍛", "🍣", "🍱", "🥟", "🦪", "🍤", "🍙", "🍚", "🍘", "🍥", "🥠", "🥮", "🍢", "🍡", "🍧",
                "🍨", "🍦", "🥧", "🧁", "🍰", "🎂", "🍮", "🍭", "🍬", "🍫", "🍿", "🍩", "🍪", "🌰", "🥜", "🍯",
                "🥛", "🍼", "☕", "🫖", "🍵", "🧃", "🥤", "🧋", "🍶", "🍺", "🍻", "🥂", "🍷", "🥃", "🍸", "🍹",
            ],
        },
        {
            id: "activities",
            label: "Activity",
            icon: "bi-trophy",
            emojis: [
                "⚽", "🏀", "🏈", "⚾", "🥎", "🎾", "🏐", "🏉", "🥏", "🎱", "🪀", "🏓", "🏸", "🏒", "🏑", "🥍",
                "🏏", "🪃", "🥅", "⛳", "🪁", "🏹", "🎣", "🤿", "🥊", "🥋", "🎽", "🛹", "🛼", "🛷", "⛸", "🥌",
                "🎿", "⛷", "🏂", "🪂", "🏋️", "🤼", "🤸", "⛹️", "🤺", "🤾", "🏌️", "🏇", "🧘", "🏄", "🏊", "🤽",
                "🚣", "🧗", "🚴", "🚵", "🎪", "🎭", "🩰", "🎨", "🎬", "🎤", "🎧", "🎼", "🎹", "🥁", "🪘", "🎷",
                "🎺", "🪗", "🎸", "🪕", "🎻", "🎲", "♟", "🎯", "🎳", "🎮", "🎰", "🧩",
            ],
        },
        {
            id: "travel",
            label: "Travel & Places",
            icon: "bi-airplane",
            emojis: [
                "🚗", "🚕", "🚙", "🚌", "🚎", "🏎", "🚓", "🚑", "🚒", "🚐", "🛻", "🚚", "🚛", "🚜", "🦯", "🦽",
                "🦼", "🛴", "🚲", "🛵", "🏍", "🛺", "🚨", "🚔", "🚍", "🚘", "🚖", "🚡", "🚠", "🚟", "🚃", "🚋",
                "🚞", "🚝", "🚄", "🚅", "🚈", "🚂", "🚆", "🚇", "🚊", "🚉", "✈️", "🛫", "🛬", "🛩", "💺", "🛰",
                "🚀", "🛸", "🚁", "🛶", "⛵", "🚤", "🛥", "🛳", "⛴", "🚢", "⚓", "🪝", "⛽", "🚧", "🚦", "🚥",
                "🗺", "🗿", "🗽", "🗼", "🏰", "🏯", "🏟", "🎡", "🎢", "🎠", "⛲", "⛱", "🏖", "🏝", "🏜", "🌋",
                "⛰", "🏔", "🗻", "🏕", "⛺", "🏠", "🏡", "🏘", "🏚", "🏗", "🏭", "🏢", "🏬", "🏣", "🏤", "🏥",
            ],
        },
        {
            id: "objects",
            label: "Objects",
            icon: "bi-lightbulb",
            emojis: [
                "⌚", "📱", "📲", "💻", "⌨️", "🖥", "🖨", "🖱", "🖲", "🕹", "🗜", "💽", "💾", "💿", "📀", "📼",
                "📷", "📸", "📹", "🎥", "📽", "🎞", "📞", "☎️", "📟", "📠", "📺", "📻", "🎙", "🎚", "🎛", "🧭",
                "⏱", "⏲", "⏰", "🕰", "⌛", "⏳", "📡", "🔋", "🔌", "💡", "🔦", "🕯", "🪔", "🧯", "🛢", "💸",
                "💵", "💴", "💶", "💷", "🪙", "💰", "💳", "💎", "⚖️", "🪜", "🧰", "🪛", "🔧", "🔨", "⚒", "🛠",
                "⛏", "🪚", "🔩", "⚙️", "🪤", "🧱", "⛓", "🧲", "🔫", "💣", "🧨", "🪓", "🔪", "🗡", "⚔️", "🛡",
                "🚬", "⚰️", "🪦", "⚱️", "🏺", "🔮", "📿", "🧿", "💈", "⚗️", "🔭", "🔬", "🕳", "🩹", "🩺", "💊",
            ],
        },
        {
            id: "symbols",
            label: "Symbols",
            icon: "bi-heart",
            emojis: [
                "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "💔", "❣️", "💕", "💞", "💓", "💗", "💖",
                "💘", "💝", "💟", "☮️", "✝️", "☪️", "🕉", "☸️", "✡️", "🔯", "🕎", "☯️", "☦️", "🛐", "⛎", "♈",
                "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓", "🆔", "⚛️", "🉑", "☢️", "☣️", "📴", "📳",
                "🈶", "🈚", "🈸", "🈺", "🈷️", "✴️", "🆚", "💮", "🉐", "㊙️", "㊗️", "🈴", "🈵", "🈹", "🈲", "🅰️",
                "🅱️", "🆎", "🆑", "🅾️", "🆘", "❌", "⭕", "🛑", "⛔", "📛", "🚫", "💯", "💢", "♨️", "🚷", "🚯",
                "🚳", "🚱", "🔞", "📵", "🚭", "✅", "☑", "✔️", "✖️", "❌", "➕", "➖", "➗", "➰", "➿", "〽️", "✳️",
            ],
        },
        {
            id: "flags",
            label: "Flags",
            icon: "bi-flag",
            emojis: [
                "🏳️", "🏴", "🏁", "🚩", "🏳️‍🌈", "🏳️‍⚧️", "🇺🇳", "🇺🇸", "🇬🇧", "🇨🇦", "🇦🇺", "🇩🇪", "🇫🇷", "🇮🇹", "🇪🇸", "🇵🇹",
                "🇧🇷", "🇲🇽", "🇦🇷", "🇨🇱", "🇯🇵", "🇰🇷", "🇨🇳", "🇮🇳", "🇵🇰", "🇧🇩", "🇹🇭", "🇻🇳", "🇮🇩", "🇵🇭", "🇲🇾", "🇸🇬",
                "🇲🇲", "🇰🇭", "🇱🇦", "🇳🇵", "🇱🇰", "🇸🇦", "🇦🇪", "🇹🇷", "🇮🇱", "🇪🇬", "🇿🇦", "🇳🇬", "🇰🇪", "🇷🇺", "🇺🇦", "🇵🇱",
            ],
        },
    ];

    const STICKER_PACKS = [
        {
            id: "reactions",
            name: "Reactions",
            stickers: ["😀", "😂", "😍", "🥰", "😎", "🤔", "😴", "😭", "😡", "🤯", "🥳", "🥺", "👍", "👎", "👏", "🙏", "🔥", "💯", "❤️", "💔", "✨", "🎉", "👀", "💪"],
        },
        {
            id: "animals",
            name: "Animals",
            stickers: ["🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯", "🦁", "🐮", "🐷", "🐸", "🐵", "🦄", "🐝", "🦋", "🐢", "🐙", "🐬", "🐳", "🐥", "🦉"],
        },
        {
            id: "food",
            name: "Food",
            stickers: ["🍕", "🍔", "🍟", "🌭", "🍿", "🧁", "🍩", "🍪", "🍫", "🍰", "🍦", "🍓", "🍉", "🍎", "🥑", "🍣", "🍜", "☕", "🧋", "🍺", "🍷", "🥤", "🧃", "🍯"],
        },
    ];

    const QUICK_REACTIONS = ["❤️", "👍", "👎", "🎉", "😂", "😮", "😢", "🔥"];
    const RECENT_KEY = "mezali-emoji-recent";

    function getRecent() {
        try {
            return JSON.parse(localStorage.getItem(RECENT_KEY) || "[]");
        } catch {
            return [];
        }
    }

    function pushRecent(emoji) {
        const next = [emoji, ...getRecent().filter((item) => item !== emoji)].slice(0, 32);
        localStorage.setItem(RECENT_KEY, JSON.stringify(next));
    }

    function isSafeGifUrl(url) {
        try {
            const parsed = new URL(url);
            if (parsed.protocol !== "https:") return false;
            const host = parsed.hostname.toLowerCase();
            return (
                host.endsWith("giphy.com") ||
                host.endsWith("tenor.com") ||
                host.endsWith("giphy.gif") ||
                host.includes("media.tenor") ||
                host.includes("media.giphy")
            );
        } catch {
            return false;
        }
    }

    function decodeEscapedText(value) {
        if (!value || typeof value !== "string") return value;
        if (!/\\u[0-9a-fA-F]{4}/i.test(value)) return value;
        return value.replace(/\\u([0-9a-fA-F]{4})/gi, (_, hex) =>
            String.fromCharCode(parseInt(hex, 16))
        );
    }

    window.ChatMedia = {
        EMOJI_CATEGORIES,
        STICKER_PACKS,
        QUICK_REACTIONS,
        getRecent,
        pushRecent,
        isSafeGifUrl,
        decodeEscapedText,
        parseBody(body) {
            body = decodeEscapedText(body || "");
            if (!body) return { type: "empty" };
            if (body.startsWith("gif:")) {
                const url = body.slice(4).trim();
                return isSafeGifUrl(url) ? { type: "gif", url } : { type: "text", text: body };
            }
            if (body.startsWith("sticker:")) {
                return { type: "sticker", emoji: decodeEscapedText(body.slice(8)) };
            }
            return { type: "text", text: body };
        },
        renderBodyInto(container, body) {
            container.replaceChildren();
            const parsed = this.parseBody(body);
            if (parsed.type === "gif") {
                const img = document.createElement("img");
                img.className = "chat-gif";
                img.src = parsed.url;
                img.alt = "GIF";
                img.loading = "lazy";
                container.appendChild(img);
                container.classList.add("is-media");
                return;
            }
            if (parsed.type === "sticker") {
                const sticker = document.createElement("div");
                sticker.className = "chat-sticker";
                sticker.textContent = parsed.emoji;
                container.appendChild(sticker);
                container.classList.add("is-sticker");
                return;
            }
            if (parsed.type === "text") {
                const text = document.createElement("div");
                text.className = "chat-bubble-text";
                text.textContent = parsed.text;
                container.appendChild(text);
            }
        },
    };
})();
