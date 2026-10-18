using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;

internal sealed class LocalSession
{
    internal string Url, Token;
    internal static string LocalData { get { return Environment.GetEnvironmentVariable("LOCALAPPDATA") ?? Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData); } }
    internal static Dictionary<string, object> Json(string text) { return new JavaScriptSerializer().Deserialize<Dictionary<string, object>>(text); }
    internal Dictionary<string, object> Request(string path, string body = null)
    {
        var request = (HttpWebRequest)WebRequest.Create(Url + "/api/" + path);
        request.Proxy = null; request.AllowAutoRedirect = false; request.Timeout = 4000;
        request.ReadWriteTimeout = 4000; request.Headers["X-Classica-Token"] = Token;
        if (body != null) {
            request.Method = "POST"; request.ContentType = "application/json";
            byte[] bytes = Encoding.UTF8.GetBytes(body); request.ContentLength = bytes.Length;
            using (var stream = request.GetRequestStream()) stream.Write(bytes, 0, bytes.Length);
        }
        using (var response = (HttpWebResponse)request.GetResponse())
        using (var stream = new StreamReader(response.GetResponseStream())) {
            if (response.StatusCode != HttpStatusCode.OK) throw new IOException("Resposta local inválida.");
            string text = stream.ReadToEnd();
            if (text.Length > 65536) throw new IOException("Resposta local muito grande.");
            return Json(text);
        }
    }
    internal static LocalSession Load()
    {
        string file = Path.Combine(LocalData, "Classica", "instancia.json");
        if (new FileInfo(file).Length > 16384) throw new IOException("Sessão inválida.");
        var data = Json(File.ReadAllText(file, Encoding.UTF8));
        string url = (string)data["url"], token = (string)data["token"];
        if (!Regex.IsMatch(url, @"\Ahttp://127\.0\.0\.1:[1-9][0-9]{0,4}\z") ||
            !Regex.IsMatch(token, @"\A[A-Za-z0-9_-]{32,128}\z") ||
            !String.Equals(Path.GetFullPath((string)data["directory"]).TrimEnd('\\'), Path.GetFullPath(Program.Root).TrimEnd('\\'), StringComparison.OrdinalIgnoreCase))
            throw new IOException("A sessão pertence a outra instalação.");
        var session = new LocalSession { Url = url, Token = token };
        var live = session.Request("instance");
        foreach (string key in new[] { "pid", "version", "directory" })
            if (!String.Equals(Convert.ToString(data[key]), Convert.ToString(live[key]), StringComparison.OrdinalIgnoreCase))
                throw new IOException("A sessão local não foi confirmada.");
        return session;
    }
}

// One visible controller per package/user. It owns only its local server and
// closes when that server ends; there is no service or Windows autostart.
internal sealed class DesktopContext : ApplicationContext
{
    private readonly NotifyIcon tray;
    private readonly Control dispatch = new Control();
    private readonly System.Windows.Forms.Timer timer = new System.Windows.Forms.Timer();
    private readonly RegisteredWaitHandle openWait, exitWait;
    private LocalSession session;
    private bool polling, busy, ending;
    private int missed;
    internal int Result;
    private bool restartRequested;

    internal static int? ForwardInstalled(string[] args)
    {
        string managed = Path.Combine(LocalSession.LocalData, "Programs", "Classica");
        if (!String.Equals(Path.GetFullPath(AppDomain.CurrentDomain.BaseDirectory).TrimEnd('\\'), managed.TrimEnd('\\'), StringComparison.OrdinalIgnoreCase)) return null;
        var record = LocalSession.Json(File.ReadAllText(Path.Combine(LocalSession.LocalData, "Classica", "instalacao.json"), Encoding.UTF8));
        var current = (Dictionary<string, object>)record["current"];
        string version = (string)current["version"];
        if (!Regex.IsMatch(version, @"\A[0-9]+\.[0-9]+\.[0-9]+\z")) throw new IOException("Instalação inválida.");
        string target = Path.Combine(managed, "versoes", "Classica-" + version, "Clássica.exe");
        if (args.Length > 1 || (args.Length == 1 && args[0] != "--check" && args[0] != "--exit")) throw new ArgumentException("Parâmetro inválido.");
        var process = Process.Start(new ProcessStartInfo(target, args.Length == 1 ? args[0] : "") { UseShellExecute = true });
        if (args.Length == 1) { process.WaitForExit(); return process.ExitCode; }
        process.Dispose(); return 0;
    }

    internal static int Run(string[] args)
    {
        string identity = LocalSession.LocalData + "|" + Path.GetFullPath(Program.Root).ToUpperInvariant();
        string name;
        using (var hash = SHA256.Create()) name = "Local\\Classica-" + BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(identity))).Replace("-", "");
        bool first;
        using (var mutex = new Mutex(true, name, out first))
        using (var open = new EventWaitHandle(false, EventResetMode.AutoReset, name + "-open"))
        using (var exit = new EventWaitHandle(false, EventResetMode.AutoReset, name + "-exit")) {
            // An old controller may be disposing just after Sair. Take over if
            // it released its mutex, instead of sending an event into the gap.
            if (!first) {
                try { first = mutex.WaitOne(200); }
                catch (AbandonedMutexException) { first = true; }
            }
            if (!first) { (args.Length == 1 ? exit : open).Set(); return 0; }
            if (args.Length == 1) { mutex.ReleaseMutex(); return 0; }
            int result = 0; bool restart = false;
            try {
                using (var context = new DesktopContext(open, exit)) {
                    Application.Run(context); result = context.Result; restart = context.restartRequested;
                }
            } finally { mutex.ReleaseMutex(); }
            if (restart) Process.Start(new ProcessStartInfo(Application.ExecutablePath) { UseShellExecute = true });
            return result;
        }
    }

    private DesktopContext(EventWaitHandle open, EventWaitHandle exit)
    {
        dispatch.CreateControl();
        var menu = new ContextMenuStrip();
        menu.Items.Add("Abrir Clássica", null, delegate { Open(); });
        menu.Items.Add("Encerrar Clássica", null, delegate { Stop(); });
        tray = new NotifyIcon { Text = "Clássica · Áudio e vídeo", Icon = System.Drawing.Icon.ExtractAssociatedIcon(Application.ExecutablePath), ContextMenuStrip = menu, Visible = true };
        tray.DoubleClick += delegate { Open(); };
        openWait = ThreadPool.RegisterWaitForSingleObject(open, delegate { Post(Open); }, null, -1, false);
        exitWait = ThreadPool.RegisterWaitForSingleObject(exit, delegate { Post(Stop); }, null, -1, false);
        timer.Interval = 1500; timer.Tick += Poll;
        var start = new StartupWindow();
        start.Completed += delegate(int code) {
            if (code != 0) { Result = code; ExitThread(); return; }
            try { session = LocalSession.Load(); timer.Start(); Poll(null, EventArgs.Empty); }
            catch (Exception e) { MessageBox.Show(e.Message, "Clássica"); Result = 1; ExitThread(); }
        };
        start.Show();
    }
    private void Post(Action action) { try { dispatch.BeginInvoke(action); } catch (InvalidOperationException) { } }
    private async void Open()
    {
        if (session == null || busy) return;
        bool closed = ending;
        if (!closed) {
            try { var live = await Task.Run(() => session.Request("instance")); closed = Convert.ToBoolean(live["closing"]); }
            catch (Exception) { closed = true; }
        }
        if (closed) { restartRequested = true; ExitThread(); return; }
        try { Process.Start(new ProcessStartInfo(session.Url) { UseShellExecute = true }); }
        catch (Exception) { MessageBox.Show("Não foi possível abrir o navegador padrão.", "Clássica"); }
    }
    private async void Stop()
    {
        if (session == null || busy || ending) return;
        try {
            var state = await Task.Run(() => session.Request("desktop"));
            if (Convert.ToInt32(state["pending"]) > 0 && MessageBox.Show("Existem downloads pendentes. Encerrar e interromper a fila?", "Clássica", MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes) return;
            await Task.Run(() => session.Request("shutdown", "{}"));
            ending = true;
            ExitThread();
        } catch (Exception) { MessageBox.Show("Não foi possível encerrar agora. Aguarde a manutenção ou use Sair na aplicação.", "Clássica"); }
    }
    private async void Poll(object sender, EventArgs args)
    {
        if (polling || busy || session == null) return;
        polling = true;
        try {
            var state = await Task.Run(() => session.Request("desktop")); missed = 0;
            var action = state["action"] as Dictionary<string, object>;
            if (action != null) {
                string id = (string)action["id"];
                if (!Regex.IsMatch(id, @"\A[a-f0-9]{32}\z")) throw new IOException("Preparação inválida.");
                busy = true;
                await Task.Run(() => session.Request("desktop/preparing", "{\"id\":\"" + id + "\"}"));
                var window = new StartupWindow(@"scripts\update_app.ps1", "-ActionId " + id);
                window.Completed += delegate(int code) {
                    if (code == 0) { ExitThread(); return; }
                    busy = false; missed = 0;
                    try { session = LocalSession.Load(); session.Request("desktop/failed", "{\"id\":\"" + id + "\"}"); } catch (Exception) { }
                };
                window.Show();
            }
        } catch (Exception) {
            if (busy) { busy = false; MessageBox.Show("Não foi possível iniciar a preparação. Tente novamente pela Ajuda.", "Clássica"); }
            else if (++missed >= 3) ExitThread();
        }
        finally { polling = false; }
    }
    protected override void Dispose(bool disposing)
    {
        if (disposing) { timer.Stop(); timer.Dispose(); openWait.Unregister(null); exitWait.Unregister(null); tray.Visible = false; tray.Dispose(); dispatch.Dispose(); }
        base.Dispose(disposing);
    }
}
