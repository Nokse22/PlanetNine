import json
from gi.repository import GObject, GtkSource, Gio
import socket
import asyncio
import threading


class Proposal(GObject.GObject, GtkSource.CompletionProposal):

    string = ""

    def __init__(self, _string):
        super().__init__()

        self.string = _string


class LSPCompletionProvider(GObject.Object, GtkSource.CompletionProvider):
    def __init__(self):
        super().__init__()
        self.socket = None
        self.message_id = 0
        self.initialize_lsp()

    def initialize_lsp(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect(("localhost", 2087))

        threading.Thread(target=self.listen, daemon=True).start()

        self.send_request("initialize", {
            "processId": None,
            "rootUri": None,
            "capabilities": {}
        })
        self.send_notification("initialized", {})

    def listen(self):
        buffer = ""
        content_length = None
        while True:
            try:
                data = self.socket.recv(4096).decode('utf-8')
                if not data:
                    break
                buffer += data
                while True:
                    if content_length is None:
                        if '\r\n\r\n' in buffer:
                            header, buffer = buffer.split('\r\n\r\n', 1)
                            headers = header.split('\r\n')
                            for h in headers:
                                if h.startswith('Content-Length: '):
                                    content_length = int(
                                        h.split('Content-Length: ')[1])
                                    break
                        else:
                            break
                    if content_length is not None and len(
                            buffer) >= content_length:
                        message = buffer[:content_length]
                        buffer = buffer[content_length:]
                        content_length = None
                        self.handle_message(json.loads(message))
                    else:
                        break
            except Exception as e:
                print(f"Error in LSP listener: {e}")
                break

    def handle_message(self, message):
        print(f"Received message: {message}")

    def send_request(self, method, params):
        self.message_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.message_id,
            "method": method,
            "params": params
        }
        self.send_message(request)
        return self.message_id

    def send_notification(self, method, params):
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        self.send_message(notification)

    def send_message(self, message):
        content = json.dumps(message)
        header = f"Content-Length: {len(content)}\r\n\r\n"
        self.socket.sendall(header.encode('utf-8') + content.encode('utf-8'))

    def do_get_name(self):
        return "Python LSP Completion"

    def do_get_priority(self, *_args):
        return 200

    def do_match(self, context):
        return True

    def do_populate_async(self, context, cancellable, callback, user_data):
        bounds = context.get_bounds()

        if isinstance(bounds, tuple) and len(bounds) == 3:
            _, start, end = bounds
        else:
            print(f"Unexpected format for bounds: {bounds}")

        buffer = context.get_buffer()
        text = buffer.get_text(
            buffer.get_start_iter(),
            buffer.get_end_iter(),
            True)
        line = end.get_line()
        character = end.get_line_offset()

        print(text)
        print(line)
        print(character)

        results = Gio.ListStore()

        results.append(Proposal(f"{text}"))

        context.set_proposals_for_provider(self, results)

    async def populate(self, context, cancellable, callback, line, character):
        try:
            request_id = await asyncio.to_thread(
                self.send_request,
                "textDocument/completion", {
                    "textDocument": {"uri": "/"},
                    "position": {"line": line, "character": character},
                    "context": {"triggerKind": 1}
                }
            )

        except Exception as e:
            print(f"Error fetching completions: {e}")

    def do_activate_proposal(self, context, proposal):
        buffer = context.get_iter().get_buffer()
        buffer.begin_user_action()
        buffer.insert(context.get_iter(), proposal.get_text())
        buffer.end_user_action()
        return True

    def do_display(self, context, proposal, cell):
        if cell.get_column() == GtkSource.CompletionColumn.TYPED_TEXT:
            cell.set_text(proposal.string)

    def register(self, buffer):
        pass

    def unregister(self, buffer):
        pass


class WordsCompletionProvider(GtkSource.CompletionWords):
    def do_display(self, context, proposal, cell):
        if cell.get_column() == GtkSource.CompletionColumn.TYPED_TEXT:
            cell.set_text(proposal.props.word)
