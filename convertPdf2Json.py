import os
import subprocess
from tqdm import tqdm  # For progress bars
import time
import sys

class ConvertPdf2Json:
    def __init__(self, pdf_folder, output_dir, mode):
        self.pdf_folder = pdf_folder
        self.output_dir = output_dir
        self.mode = mode
        self.success_count = 0
        self.failure_count = 0
        self.processed_files = []
        self.failed_files = []

    def _validate_paths(self):
        """Validate input and output paths exist"""
        if not os.path.exists(self.pdf_folder):
            raise FileNotFoundError(f"PDF folder not found: {self.pdf_folder}")
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"Created output directory: {self.output_dir}")

    def _get_pdf_files(self):
        """Get list of PDF files to process"""
        pdf_files = []
        for root, _, files in os.walk(self.pdf_folder):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
        
        if not pdf_files:
            raise ValueError(f"No PDF files found in: {self.pdf_folder}")
            
        return pdf_files

    def _run_conversion(self, pdf_file, pbar):
        """Run the actual conversion for a single file"""
        try:
            # 更新进度条显示当前文件
            pbar.set_description(f"Converting: {os.path.basename(pdf_file)}")
            pbar.refresh()
            
            # Get relative path for output structure
            rel_path = os.path.relpath(pdf_file, self.pdf_folder)
            output_path = os.path.join(self.output_dir, rel_path)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Run the conversion command
            cmd = f"magic-pdf -p {pdf_file} -o {output_path} -m {self.mode}"
            
            # 使用Popen来实时监控进程
            process = subprocess.Popen(
                cmd, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # 实时更新进度条
            while process.poll() is None:
                time.sleep(0.1)  # 100ms更新一次
                pbar.refresh()
                sys.stdout.flush()
            
            # 获取最终结果
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                self.success_count += 1
                self.processed_files.append(pdf_file)
                pbar.set_postfix_str(f"✅ {os.path.basename(pdf_file)}")
                return True
            else:
                error_msg = f"magic-pdf failed: {stderr.strip()}"
                self.failure_count += 1
                self.failed_files.append((pdf_file, error_msg))
                pbar.set_postfix_str(f"❌ {os.path.basename(pdf_file)}")
                return False
            
        except Exception as e:
            error_msg = f"Unexpected error converting {pdf_file}: {str(e)}"
            self.failure_count += 1
            self.failed_files.append((pdf_file, error_msg))
            pbar.set_postfix_str(f"❌ {os.path.basename(pdf_file)}")
            return False

    def convert(self):
        """Main conversion method with progress tracking"""
        print(f"\nStarting PDF conversion from {self.pdf_folder} to {self.output_dir}")
        print(f"Mode: {self.mode}\n")
        
        try:
            # Validate paths first
            self._validate_paths()
            
            # Get all PDF files
            pdf_files = self._get_pdf_files()
            total_files = len(pdf_files)
            
            print(f"Found {total_files} PDF files to process\n")
            
            # Process files with progress bar
            with tqdm(
                total=total_files, 
                desc="Converting PDFs", 
                unit="file",
                ncols=120,  # 更宽的进度条
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}] {postfix}'
            ) as pbar:
                for i, pdf_file in enumerate(pdf_files):
                    pbar.set_description(f"Processing file {i+1}/{total_files}")
                    self._run_conversion(pdf_file, pbar)
                    pbar.update(1)
                    # 强制更新进度条显示
                    pbar.set_postfix({
                        'success': self.success_count,
                        'failed': self.failure_count
                    })
                    pbar.refresh()
                    
            # Print summary
            print("\nConversion Summary:")
            print(f"  Successfully converted: {self.success_count} files")
            print(f"  Failed conversions: {self.failure_count} files")
            
            if self.failed_files:
                print("\nFailed files:")
                for file, error in self.failed_files:
                    print(f"  - {file}: {error}")
                    
            return self.success_count == total_files
            
        except Exception as e:
            print(f"\nFatal error during conversion: {str(e)}")
            return False