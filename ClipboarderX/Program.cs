using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace ClipboarderX
{
    static class Program
    {
        /// <summary>
        /// アプリケーションのメイン エントリ ポイントです。
        /// </summary>
        [STAThread]
        static void Main(string[] args)
        {
            int port = 0;
            if (args.Length < 2 || !int.TryParse(args[1], out port))
            {
                MessageBox.Show(
                    "Please specify the target IP address and port number as command-line arguments.\nExample: ClipboarderX.exe 192.168.1.50 50000",
                    "ClipboarderX",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Information);
                return;
            }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new Form1(args[0], port));
        }
    }
}
