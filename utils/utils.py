import os

def get_files_with_extension(directory, extension):

    if extension.startswith('.'):
        extension = extension[1:]
        
    files = []
    for filename in os.listdir(directory):
        # print("Filename",filename)
        if filename.endswith(f".{extension}"):
            files.append(os.path.abspath(os.path.join(directory,filename)).replace('\\\\','\\'))
    print(files)
    return files


if __name__ =="__main__":
    get_files_with_extension(f'reference_audios\emotions','wav')