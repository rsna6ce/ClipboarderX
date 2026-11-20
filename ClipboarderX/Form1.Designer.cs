
namespace ClipboarderX
{
    partial class Form1
    {
        /// <summary>
        /// 必要なデザイナー変数です。
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// 使用中のリソースをすべてクリーンアップします。
        /// </summary>
        /// <param name="disposing">マネージド リソースを破棄する場合は true を指定し、その他の場合は false を指定します。</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows フォーム デザイナーで生成されたコード

        /// <summary>
        /// デザイナー サポートに必要なメソッドです。このメソッドの内容を
        /// コード エディターで変更しないでください。
        /// </summary>
        private void InitializeComponent()
        {
            this.labelTarget = new System.Windows.Forms.Label();
            this.labelStatus = new System.Windows.Forms.Label();
            this.labelSendCount = new System.Windows.Forms.Label();
            this.labelRecvCount = new System.Windows.Forms.Label();
            this.SuspendLayout();
            // 
            // labelTarget
            // 
            this.labelTarget.AutoSize = true;
            this.labelTarget.Location = new System.Drawing.Point(8, 8);
            this.labelTarget.Name = "labelTarget";
            this.labelTarget.Size = new System.Drawing.Size(62, 12);
            this.labelTarget.TabIndex = 0;
            this.labelTarget.Text = "labelTarget";
            // 
            // labelStatus
            // 
            this.labelStatus.AutoSize = true;
            this.labelStatus.Location = new System.Drawing.Point(8, 28);
            this.labelStatus.Name = "labelStatus";
            this.labelStatus.Size = new System.Drawing.Size(62, 12);
            this.labelStatus.TabIndex = 0;
            this.labelStatus.Text = "labelStatus";
            // 
            // labelSendCount
            // 
            this.labelSendCount.AutoSize = true;
            this.labelSendCount.Location = new System.Drawing.Point(8, 48);
            this.labelSendCount.Name = "labelSendCount";
            this.labelSendCount.Size = new System.Drawing.Size(84, 12);
            this.labelSendCount.TabIndex = 0;
            this.labelSendCount.Text = "labelSendCount";
            // 
            // labelRecvCount
            // 
            this.labelRecvCount.AutoSize = true;
            this.labelRecvCount.Location = new System.Drawing.Point(8, 64);
            this.labelRecvCount.Name = "labelRecvCount";
            this.labelRecvCount.Size = new System.Drawing.Size(85, 12);
            this.labelRecvCount.TabIndex = 0;
            this.labelRecvCount.Text = "labelRecvCount";
            // 
            // Form1
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 12F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(292, 186);
            this.Controls.Add(this.labelRecvCount);
            this.Controls.Add(this.labelSendCount);
            this.Controls.Add(this.labelStatus);
            this.Controls.Add(this.labelTarget);
            this.FormBorderStyle = System.Windows.Forms.FormBorderStyle.FixedToolWindow;
            this.MaximizeBox = false;
            this.Name = "Form1";
            this.Text = "ClipboarderX";
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion

        private System.Windows.Forms.Label labelTarget;
        private System.Windows.Forms.Label labelStatus;
        private System.Windows.Forms.Label labelSendCount;
        private System.Windows.Forms.Label labelRecvCount;
    }
}

