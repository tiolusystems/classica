using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

[assembly: AssemblyTitle("Clássica")]
[assembly: AssemblyDescription("Inicialização da Clássica — by ☧ SYSTEMS")]
[assembly: AssemblyCompany("☧ SYSTEMS")]
[assembly: AssemblyProduct("Clássica")]
[assembly: AssemblyVersion("2.1.2.0")]
[assembly: AssemblyFileVersion("2.1.2.0")]

internal static class Program
{
    internal static readonly string Root = AppDomain.CurrentDomain.BaseDirectory;

    internal static void CheckPackage()
    {
        if (!Environment.Is64BitOperatingSystem)
            throw new InvalidOperationException("Esta versão requer Windows 10 ou 11 de 64 bits (Intel/AMD).");
        foreach (string name in new[] { "iniciar.ps1", "app.py", "tools.lock.json", "requirements.lock" })
            if (!File.Exists(Path.Combine(Root, name)))
                throw new FileNotFoundException("Extraia a pasta Classica completa do ZIP antes de abrir a aplicação. Arquivo ausente: " + name);
    }

    [STAThread]
    private static int Main(string[] args)
    {
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        try
        {
            CheckPackage();
            if (args.Length == 1 && args[0] == "--check") return 0;
            if (args.Length != 0) throw new ArgumentException("Abra Clássica sem parâmetros.");
            Application.Run(new StartupWindow());
            return StartupWindow.Result;
        }
        catch (Exception error)
        {
            if (args.Length == 0)
                MessageBox.Show(error.Message, "Clássica", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}

internal sealed class StartupWindow : Form
{
    internal static int Result = 1;
    private readonly TextBox details;
    private readonly Label status;
    private readonly ProgressBar progress;
    private Process child;
    private bool finished;
    private readonly object logLock = new object();

    internal StartupWindow()
    {
        Text = "Clássica · 2.1.2";
        Icon = System.Drawing.Icon.ExtractAssociatedIcon(Application.ExecutablePath);
        StartPosition = FormStartPosition.CenterScreen;
        AutoScaleMode = AutoScaleMode.Dpi;
        ClientSize = new Size(560, 300);
        MinimumSize = new Size(440, 280);
        BackColor = Color.FromArgb(247, 248, 246);
        ForeColor = Color.FromArgb(23, 43, 58);
        Font = new Font("Segoe UI", 10);
        var layout = new TableLayoutPanel { Dock = DockStyle.Fill, Padding = new Padding(20), ColumnCount = 1, RowCount = 5 };
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        layout.Controls.Add(new Label { Text = "Clássica 2.1.2", AutoSize = true, Font = new Font("Segoe UI", 20), Margin = new Padding(0, 0, 0, 10) });
        status = new Label { Text = "Preparando sua biblioteca…", AutoSize = true, Dock = DockStyle.Fill, Margin = new Padding(0, 0, 0, 12) };
        layout.Controls.Add(status);
        progress = new ProgressBar { Style = ProgressBarStyle.Marquee, Dock = DockStyle.Fill, Height = 5, Margin = new Padding(0, 0, 0, 12) };
        layout.Controls.Add(progress);
        details = new TextBox { Multiline = true, ReadOnly = true, ScrollBars = ScrollBars.Vertical, Dock = DockStyle.Fill, BackColor = Color.White, BorderStyle = BorderStyle.FixedSingle, AccessibleName = "Detalhes da preparação" };
        layout.Controls.Add(details);
        layout.Controls.Add(new Label { Text = "by ☧ SYSTEMS", AutoSize = true, Margin = new Padding(0, 12, 0, 0) });
        Controls.Add(layout);
        Shown += Start;
        FormClosing += delegate(object sender, FormClosingEventArgs e) {
            // Do not abandon downloads or terminate the detached application.
            if (!finished) { e.Cancel = true; status.Text = "Aguarde a preparação terminar para fechar esta janela."; }
        };
    }

    private void Append(string line)
    {
        if (line != null) {
            try { lock (logLock) File.AppendAllText(Path.Combine(Program.Root, "ultimo-lancador.log"), line + Environment.NewLine, System.Text.Encoding.UTF8); }
            catch (IOException) { }
            catch (UnauthorizedAccessException) { }
        }
        if (line == null || IsDisposed) return;
        try { BeginInvoke((Action)delegate { if (!IsDisposed) details.AppendText(line + Environment.NewLine); }); }
        catch (InvalidOperationException) { }
    }

    private async void Start(object sender, EventArgs args)
    {
        try
        {
            details.AppendText("Na primeira abertura, os componentes serão preparados. Isso pode levar alguns minutos e requer internet e cerca de 2 GB livres.\r\n\r\n");
            // Use the system PowerShell, never an executable found through PATH.
            string powershell = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), @"WindowsPowerShell\v1.0\powershell.exe");
            child = new Process();
            child.StartInfo = new ProcessStartInfo {
                FileName = powershell,
                Arguments = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File \"" + Path.Combine(Program.Root, "iniciar.ps1") + "\" -Background",
                WorkingDirectory = Program.Root,
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true
            };
            child.OutputDataReceived += delegate(object s, DataReceivedEventArgs e) { Append(e.Data); };
            child.ErrorDataReceived += delegate(object s, DataReceivedEventArgs e) { Append(e.Data); };
            child.Start();
            Append("Inicializador iniciado.");
            child.BeginOutputReadLine();
            child.BeginErrorReadLine();
            // The no-argument WaitForExit also waits for redirected pipe EOF.
            // A detached Windows process can inherit those pipe handles even
            // after PowerShell exits; wait only for the initializer process.
            await System.Threading.Tasks.Task.Run((Action)delegate { while (!child.WaitForExit(250)) { } });
            try { child.CancelOutputRead(); } catch (InvalidOperationException) { }
            try { child.CancelErrorRead(); } catch (InvalidOperationException) { }
            finished = true;
            Result = child.ExitCode;
            Append("Inicializador encerrado. Codigo: " + Result);
            if (Result == 0) { Close(); return; }
            Fail("Não foi possível abrir a Clássica. Consulte os detalhes abaixo e o arquivo ultimo-inicio.log na pasta da aplicação.");
        }
        catch (Exception error) { finished = true; Result = 1; Append(error.Message); Fail("Não foi possível iniciar. Confira os detalhes abaixo."); }
        finally { if (child != null) child.Dispose(); }
    }

    private void Fail(string message)
    {
        status.Text = message;
        progress.Style = ProgressBarStyle.Blocks;
        progress.Value = 0;
        details.Focus();
    }
}
