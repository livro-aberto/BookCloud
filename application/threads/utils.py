from application.users import User
from model import Comment, User_Tag, File_Tag, Custom_Tag, Free_Tag, Likes
from ..utils import window, rst2html

def display_threads(threads):
    # creates an object to help visualize a list of threads
    if not threads:
        return None
    response = []
    query = list(threads)
    for q in query:
        current_thread = {}
        current_thread['id'] = q.id
        current_thread['title'] = q.title
        current_thread['author'] = User.query.filter_by(id=q.owner_id).first().username
        current_thread['flag'] = q.flag
        current_thread['posted_at'] = q.posted_at
        current_thread['number'] = Comment.query.filter_by(thread_id=q.id).count()
        user_tags = User_Tag.query.filter_by(thread_id=q.id)
        current_thread['user_tags'] = [u.user.username for u in user_tags]
        file_tags = File_Tag.query.filter_by(thread_id=q.id)
        current_thread['file_tags'] = [f.filename for f in file_tags]
        custom_tags = Custom_Tag.query.filter_by(thread_id=q.id)
        current_thread['custom_tags'] = [c.named_tag.name for c in custom_tags]
        free_tags = Free_Tag.query.filter_by(thread_id=q.id)
        current_thread['free_tags'] = [f.name for f in free_tags]
        current_thread['comments'] = []

        get_comments = Comment.query.filter_by(thread_id=q.id).order_by(Comment.lineage).limit(100)
        for prev_comment, comment, next_comment  in window(get_comments):
            current_comment = {}
            current_comment['id'] = comment.id
            current_comment['author'] = User.query.filter_by(id=comment.owner_id).first().username
            current_comment['content'] = rst2html(comment.content)
            current_comment['posted_at'] = comment.posted_at
            current_comment['lineage'] = comment.lineage
            current_comment['indent'] = 6 * len(comment.lineage)
            current_comment['likes'] = Likes.query.filter_by(comment_id=comment.id).count()
            if next_comment:
                current_comment['father'] = (next_comment.lineage.startswith(comment.lineage))
            current_thread['comments'].append(current_comment)
        response.append(current_thread)

    return response
