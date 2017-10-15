
"""Module for creating pdf files for Images-discipline

This file must run in /static/images as cwd folder.
"""

import os
import random
import itertools
import subprocess
from datetime import datetime

from jinja2 import Environment, FileSystemLoader
import pysftp

latex_jinja_env = Environment(
    block_start_string='\STATEMENT{',
    block_end_string='}',
    variable_start_string='\PRINT{',
    variable_end_string='}',
    comment_start_string='\#{',
    comment_end_string='}',
    line_statement_prefix='%%',
    line_comment_prefix='%#',
    trim_blocks=True,
    autoescape=False,
    loader=FileSystemLoader('../../templates')
)


def grouper(n, iterable, fillvalue=None):
    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    chunks = itertools.zip_longest(fillvalue=fillvalue, *args)
    return (list(x) for x in chunks)


def yield_image_pages(root):
    files = list()
    for image_file in os.listdir(root):
        if image_file.endswith(('.jpg', '.png', '.bmp')):
            assert ' ' not in image_file
            files.append(f'{root}/{image_file}')
    sample = random.sample(files, 500)
    yield from grouper(10, grouper(5, sample))


def rename_space(root):
    for image_file in os.listdir(root):
        if ' ' in image_file:
            os.rename(
                src=os.path.join(root, image_file),
                dst=os.path.join(root, image_file.replace(' ', '_'))
            )


def compile_tex(prefix, tex_file):
    pdf_filename = f'{prefix}_{os.path.splitext(tex_file)[0]}'
    p = subprocess.run(['pdflatex', '--jobname', pdf_filename, tex_file])
    print(p)
    assert p.returncode == 0


def generate_sheets(prefix):

    # RELATIVE PATH TO IMAGE DATABASE
    src_images = '../src_images'

    # TEX TEMPLATES
    tex_memo = 'images_memorization.tex'
    tex_recall = 'images_recall.tex'
    tex_correction = 'images_correction.tex'

    # GET TEMPLATES
    template_memo = latex_jinja_env.get_template(tex_memo)
    template_recall = latex_jinja_env.get_template(tex_recall)
    template_correction = latex_jinja_env.get_template(tex_correction)

    # RENDER TEX FILES
    data = list(yield_image_pages(src_images))
    with open(tex_memo, 'w', encoding='utf-8') as tex:
        tex.write(template_memo.render(images=enumerate(data)))

    # Change the order of the images on each row for the recall sheet
    answer = list()
    for page in data:
        for chunk in page:
            order = [0, 1, 2, 3, 4]
            random.shuffle(order)
            copy = chunk[:]
            for i in range(len(chunk)):
                chunk[i] = copy[order[i]]
            answer.append(order)

    with open(tex_recall, 'w', encoding='utf-8') as tex:
        tex.write(template_recall.render(images=enumerate(data)))

    with open(tex_correction, 'w', encoding='utf-8') as tex:
        data = list(grouper(30, enumerate(answer, start=1)))
        tex.write(template_correction.render(images=data))

    # COMPILE TEX TO PDF
    compile_tex(prefix, tex_memo)
    compile_tex(prefix, tex_recall)
    compile_tex(prefix, tex_correction)


def old_main():
    for file in os.listdir('pdf'):
        if file.endswith('.pdf'):
            os.remove(f'./pdf/{file}')

    datestr = datetime.now().strftime('_%b_%d')
    N = 3
    for i in range(N):
        generate_sheets(str(i + 1) + datestr)

    with pysftp.Connection('ssh.pythonanywhere.com', username='penlect',
                           password='password') as sftp:
        with sftp.cd('total-recall/recall/static/images'):
            print('Files at start:')
            files_on_server = sftp.listdir()
            print(files_on_server)

            pdf_files = [file for file in files_on_server if file.endswith('.pdf')]
            for pdf_file in pdf_files:
                sftp.remove(pdf_file)
            print('Pdf files removed:')
            print(sftp.listdir())

            print('Copying new pdf files to server')
            for file in os.listdir('pdf'):
                if file.endswith('.pdf'):
                    pdf_file = f'./pdf/{file}'
                    sftp.put(pdf_file, preserve_mtime=True)
                    print(pdf_file)
            print(sftp.listdir())


def main():

    old_files = [f for f in os.listdir('.') if f.endswith(('.pdf', '.aux', '.log'))]

    datestr = datetime.now().strftime('_%b_%d')
    N = 5
    for i in range(N):
        generate_sheets(str(i + 1) + datestr)

    for pdf_file in old_files:
        os.remove(pdf_file)


if __name__ == '__main__':
    main()