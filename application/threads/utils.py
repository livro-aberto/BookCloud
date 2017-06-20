#from model import Comment, User_Tag, File_Tag, Custom_Tag, Free_Tag, Likes

def display_threads(threads):
    if not threads:
        return None
    else:
        return list(threads)
