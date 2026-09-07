const MAX_MESSAGE_BYTES = 2 * 1024 * 1024;

export function rpcError(id, code, message) {
  return { jsonrpc: "2.0", id, error: { code, message } };
}

export function toolContent(data, isError = false) {
  return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }],
    structuredContent: data, isError };
}

// Newline JSON is the standard stdio transport. Byte-counted Content-Length
// frames remain supported only for existing legacy clients.
export class MessageReader {
  constructor(onMessage, onError, maxBytes = MAX_MESSAGE_BYTES) {
    this.onMessage = onMessage;
    this.onError = onError;
    this.maxBytes = maxBytes;
    this.buffer = Buffer.alloc(0);
  }

  feed(chunk) {
    this.buffer = Buffer.concat([this.buffer, Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk)]);
    while (this.buffer.length) {
      const framed = /^content-length:/i.test(this.buffer.subarray(0, 15).toString("ascii"));
      let body, end;
      if (framed) {
        const headerEnd = this.buffer.indexOf("\r\n\r\n");
        if (headerEnd < 0) {
          if (this.buffer.length > 8192) this.fail("Invalid frame header", true);
          return;
        }
        const header = this.buffer.subarray(0, headerEnd).toString("ascii");
        const matches = [...header.matchAll(/^Content-Length:\s*(\d+)\s*$/gim)];
        if (matches.length !== 1) { this.fail("Invalid Content-Length", true); return; }
        const length = Number(matches[0][1]);
        if (!Number.isSafeInteger(length) || length < 1 || length > this.maxBytes) {
          this.fail("Message size limit exceeded", true); return;
        }
        end = headerEnd + 4 + length;
        if (this.buffer.length < end) return;
        body = this.buffer.subarray(headerEnd + 4, end);
      } else {
        const newline = this.buffer.indexOf("\n");
        if (newline < 0) {
          if (this.buffer.length > this.maxBytes) this.fail("Message size limit exceeded", false);
          return;
        }
        end = newline + 1;
        body = this.buffer.subarray(0, newline);
      }
      this.buffer = this.buffer.subarray(end);
      if (!body.length) continue;
      if (body.length > this.maxBytes) { this.onError("Message size limit exceeded", framed); continue; }
      try {
        const raw = new TextDecoder("utf-8", { fatal: true }).decode(body);
        this.onMessage(JSON.parse(raw), framed);
      } catch {
        this.onError("Invalid JSON or UTF-8", framed);
      }
    }
  }

  fail(message, framed) {
    this.buffer = Buffer.alloc(0);
    this.onError(message, framed);
  }

  end() {
    if (this.buffer.length && this.buffer.toString("utf8").trim()) this.fail("Incomplete message at end of input", false);
  }
}

export function serveStdio(handleMessage, input = process.stdin, output = process.stdout) {
  let active = 0;
  const send = (message, framed) => {
    if (!message) return;
    const payload = JSON.stringify(message);
    output.write(framed ? "Content-Length: " + Buffer.byteLength(payload) + "\r\n\r\n" + payload : payload + "\n");
  };
  const reader = new MessageReader((message, framed) => {
    if (active >= 32) {
      if (message && Object.hasOwn(message, "id")) send(rpcError(message.id, -32000, "Server busy; retry later."), framed);
      return;
    }
    active++;
    Promise.resolve().then(() => handleMessage(message))
      .then((reply) => send(reply, framed))
      .catch(() => send(rpcError(message?.id ?? null, -32603, "Internal server error"), framed))
      .finally(() => { active--; });
  }, (error, framed) => send(rpcError(null, -32700, error), framed));
  input.on("data", (chunk) => reader.feed(chunk));
  input.on("end", () => reader.end());
  return reader;
}
