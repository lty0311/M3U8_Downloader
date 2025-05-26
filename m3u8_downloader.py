import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from configparser import ConfigParser
import threading
import os
import requests
from concurrent.futures import ThreadPoolExecutor
import subprocess
from natsort import natsorted
from urllib.parse import urljoin

# 获取当前脚本所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 读取配置文件
config = ConfigParser()
config.read('config.ini')

class M3U8DownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("M3U8 下载器（QQ：290052621 虎哥）")
        self.root.geometry("600x450")
        self.root.resizable(False, False)
        
        # 禁用最大化按钮
        self.root.resizable(False, False)
        icon_path = os.path.join(current_dir, "favicon.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        # 停止标志
        self.stop_flag = False
        
        # 设置主题
        style = ttk.Style()
        style.theme_use('clam')  # 可替换为 'alt', 'default', 'classic'

        self.init_ui()

    def init_ui(self):
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # M3U8 URL 输入框
        ttk.Label(frame, text="M3U8 URL:").grid(row=0, column=0, sticky='w', pady=5)
        self.url_entry = ttk.Entry(frame, width=50)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5)

        # 输出目录选择
        ttk.Label(frame, text="输出目录:").grid(row=1, column=0, sticky='w', pady=5)
        self.output_dir_var = tk.StringVar(value=config['DEFAULT']['output_dir'])
        self.dir_entry = ttk.Entry(frame, textvariable=self.output_dir_var, width=50)
        self.dir_entry.grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(frame, text="浏览", command=self.select_output_dir).grid(row=1, column=2, padx=5, pady=5)

        # 输出文件名
        ttk.Label(frame, text="输出文件名:").grid(row=2, column=0, sticky='w', pady=5)
        self.filename_entry = ttk.Entry(frame, width=50)
        self.filename_entry.grid(row=2, column=1, padx=5, pady=5)
        self.filename_entry.insert(0, "output")

        # 是否使用 FFmpeg
        self.use_ffmpeg_var = tk.BooleanVar(value=config.getboolean('DEFAULT', 'use_ffmpeg'))
        self.ffmpeg_check = ttk.Checkbutton(frame, text="使用 FFmpeg 合并", variable=self.use_ffmpeg_var)
        self.ffmpeg_check.grid(row=3, column=1, sticky='w', pady=5)

        # 是否清除TS
        self.clean_temp_var = tk.BooleanVar(value=config.getboolean('DEFAULT', 'clean_temp'))
        self.ffmpeg_check = ttk.Checkbutton(frame, text="下载完清除TS文件", variable=self.clean_temp_var)
        self.ffmpeg_check.grid(row=4, column=1, sticky='w', pady=5)

        # 线程数设置
        ttk.Label(frame, text="线程数:").grid(row=5, column=0, sticky='w', pady=5)
        self.threads_spinbox = ttk.Spinbox(frame, from_=1, to=20, width=5)
        self.threads_spinbox.delete(0, "end")
        self.threads_spinbox.insert(0, config['DEFAULT']['threads'])
        self.threads_spinbox.grid(row=5, column=1, sticky='w', padx=5, pady=5)

        # 按钮区域
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=6, column=1, columnspan=2, pady=20)

        self.start_button = ttk.Button(btn_frame, text="开始下载", style="Accent.TButton", command=self.start_download)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(btn_frame, text="停止下载", state=tk.DISABLED, command=self.stop_download)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # 日志输出区域
        self.log_text = tk.Text(frame, height=8, width=70, wrap=tk.WORD, bg="#f9f9f9", relief="sunken")
        self.scrollbar = tk.Scrollbar(frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=self.scrollbar.set)
        self.log_text.grid(row=7, column=0, columnspan=4, pady=0, sticky="nsew")
        self.scrollbar.grid(row=7, column=3, sticky="ns")

    def select_output_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir_var.set(directory)

    def log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

    def start_download(self):
        url = self.url_entry.get().strip()
        output_dir = self.output_dir_var.get().strip()
        filename = self.filename_entry.get().strip()
        use_ffmpeg = self.use_ffmpeg_var.get()
        threads = int(self.threads_spinbox.get().strip())

        if not url:
            messagebox.showwarning("警告", "请输入有效的 M3U8 地址！")
            return

        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                messagebox.showerror("错误", f"无法创建输出目录：{e}")
                return

        # 停止标志
        self.stop_flag = False
        
        self.download_thread = threading.Thread(target=self.download_m3u8, args=(url, output_dir, filename, use_ffmpeg, threads))
        self.download_thread.start()

        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

    def stop_download(self):
        self.log("正在尝试停止下载...")
        self.stop_flag = True  # 发送停止信号给下载线程
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def download_m3u8(self, url, output_dir, filename, use_ffmpeg, threads):
        m3u8_content = requests.get(url).text
        ts_urls = [line.strip() for line in m3u8_content.splitlines() if line.endswith('.ts')]
        base_url = '/'.join(url.split('/')[:-1]) + '/'
        domain = '/'.join(base_url.split('/')[:3])
        
        downloaded_files = []
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(self.download_ts, ts_url, base_url, output_dir, idx): idx for idx, ts_url in enumerate(ts_urls)}
            for future in futures:
                if self.stop_flag:  # 如果用户点击了停止，就不再处理后续任务
                    self.log("检测到停止信号，取消剩余任务。")
                    break
                idx = futures[future]
                try:
                    future.result()  # Wait for all downloads to complete
                    downloaded_files.append(os.path.join(output_dir, f"{idx}.ts"))
                except Exception as e:
                    print(f"下载失败: {e}")
        
        if self.stop_flag:
            self.log("下载已中断，合并过程取消。")
            return
            
        if use_ffmpeg:
            self.merge_with_ffmpeg(output_dir, filename)
        else:
            # 按顺序合并TS文件
            print("Merging TS files...")
            # 按数字序号排序
            downloaded_files.sort()
            
            # 确保输出文件路径在output_dir中
            final_output_path = os.path.join(output_dir, f"{filename}.mp4")
            
            with open(final_output_path, 'wb') as merged:
                for ts_file in downloaded_files:
                    with open(ts_file, 'rb') as f:
                        merged.write(f.read())
            
            print(f"Video successfully merged and saved as {final_output_path}")
            print("下载完毕！")
            
        clean_temp = self.clean_temp_var.get()
        # 清理临时TS文件
        if clean_temp:
            print("Cleaning up temporary TS files...")
            for ts_file in downloaded_files:
                try:
                    os.remove(ts_file)
                except Exception as e:
                    print(f"Error deleting {ts_file}: {e}")
            
            print("Cleanup completed.")

        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def download_ts(self, ts_url, base_url, output_dir, idx):
        if self.stop_flag:
            self.log(f"停止信号已触发，跳过 {ts_url}")
            return
        
        # ts_full_url = base_url + ts_url
        # response = requests.get(ts_full_url)
        # ts_filename = os.path.join(output_dir, f"{idx}.ts")
        # with open(ts_filename, 'wb') as f:
        #     f.write(response.content)
        # self.log(f"已下载 {ts_url} 到 {ts_filename}")
        
        # 判断是否为绝对URL
        if ts_url.startswith(('http://', 'https://')):
            full_url = ts_url
        else:
            # 如果以 / 开头，则拼接域名部分（base_url_domain）
            if ts_url.startswith('/'):
                # base_url 是 https://w.com/obj/
                # 我们提取域名部分 https://w.com
                domain = '/'.join(base_url.split('/')[:3])  # ['https:', '', 'w.com']
                full_url = domain + ts_url
            else:
                # 普通相对路径，直接拼接 base_url
                full_url = urljoin(base_url, ts_url)
        
        try:
            response = requests.get(full_url, timeout=10)
            response.raise_for_status()
            ts_filename = os.path.join(output_dir, f"{idx}.ts")
            with open(ts_filename, 'wb') as f:
                f.write(response.content)
            self.log(f"已下载 {ts_url} 到 {ts_filename}")
        except Exception as e:
            self.log(f"下载失败: {ts_url}, 错误: {e}")

    def merge_with_ffmpeg(self, output_dir, filename):
        ffmpeg_path = os.path.abspath(config['DEFAULT']['ffmpeg_path'])
        if not os.path.exists(ffmpeg_path):
            self.log(f"错误：FFmpeg 可执行文件不存在于路径：{ffmpeg_path}")
            return
        self.log(f"FFmpeg 开始合并")
        ts_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith('.ts')]
        # 确保TS文件按自然顺序排序
        ts_files = natsorted(ts_files)

        # 检查所有TS文件是否存在
        for ts_file in ts_files:
            if not os.path.exists(ts_file):
                self.log(f"错误：TS 文件 {ts_file} 不存在")
                return

        concat_list_file = "concat_list.txt"
        with open(concat_list_file, 'w', encoding='utf-8') as f:
            for ts_file in ts_files:
                # 使用相对路径（相对于output_dir）
                f.write(f"file '{ts_file}'\n")

        final_output = os.path.join(output_dir, f"{filename}.mp4")
        cmd = [
            ffmpeg_path,
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_list_file,
            '-c', 'copy',
            final_output
        ]
        
        try:
            result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.log(f"FFmpeg 输出：{result.stdout.decode()}")
            self.log(f"使用 FFmpeg 合并完成，输出文件: {final_output}")
        except subprocess.CalledProcessError as e:
            self.log(f"FFmpeg 错误：{e.stderr.decode()}")
        
        os.remove(concat_list_file)
        print("下载完毕！")


if __name__ == "__main__":
    root = tk.Tk()
    app = M3U8DownloaderApp(root)
    root.mainloop()