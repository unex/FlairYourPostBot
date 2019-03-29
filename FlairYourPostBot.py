import os, sys
import praw
import asyncio
from concurrent.futures import ProcessPoolExecutor
import traceback

from datetime import timedelta
from time import time, sleep
from collections import OrderedDict

# Custom logging
try:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"..")))
    from utils import log

except:
    import logging
    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)

    log.addHandler(logging.StreamHandler(sys.stdout))

try:
    from asyncio import ensure_future
except ImportError:
    ensure_future = getattr(asyncio, 'async')


subreddit_name = "amd"


'''
`sleep time` : time (in seconds) the bot sleeps before performing a new check
`time_until_message` : time (in seconds) a person has to add flair before a initial message is sent
`time_until_remove` : time (in seconds) after a message is sent that a person has to add flair before the post is removed and they have to resubmit it
`h_time_intil_remove` : Human Readable Version of time_until_remove
`post_grab_limit` : how many new posts to check at a time.
`add_flair_subject_line`, `add_flair_message` : Initial Message that tells a user that they need to flair their post
`remove_post_subject_line`, `remove_post_message`: Second message telling them to resubmit their post since they have not flaired in time
`no_flair` : Posts that still have a grace period to add a flair`
'''

time_until_message = 60
time_until_remove = 1200
h_time_until_remove = str(timedelta(seconds=time_until_remove))

add_flair_subject_line = "You have not tagged your post."
add_flair_message = ("[Your recent post]({post_url}) does not have any flair and will soon be removed.\n\n"
                     "Please add flair to your post. "
                     "If you do not add flair within **" + h_time_until_remove + "**, you will have to resubmit your post. "
                     "Don't know how to flair your post? Click [here](http://imgur.com/a/m3FI3) to view this helpful guide on how to flair your post. "
                     "If you are using the mobile version of the site click the hamburger menu in the top right of the screen and switch to the desktop site and then follow the instructions as you would on desktop.")

remove_post_subject_line = "You have not tagged your post within the allotted amount of time."
remove_post_message = "[Your recent post]({post_url}) still does not have any flair and will remain removed, feel free to resubmit your post and remember to flair it once it is posted.*"

tech_support_subject_line = "Tech support removed"
tech_support_message = "Hello, I see you have a tech support problem. For the best chance at resolving your issue, please post it in our monthly tech support megathread, /r/AMDHelp, or /r/techsupport"

user_agent = ("/r/AMD bot by /u/RenegadeAI") # tells reddit the bot's purpose.
reddit = praw.Reddit('AMD', user_agent=user_agent)
subreddit = reddit.subreddit(subreddit_name)


@asyncio.coroutine
def get_subreddit_settings(name):
    raise NotImplementedError("TODO: Subreddit settings")

def check_if_ts(submission):
    # If the submission has Tech support
    if submission.link_flair_text == 'Tech Support' and submission.author not in subreddit.moderator() and not submission.approved_by:
        submission.author.message(tech_support_subject_line, tech_support_message)
        submission.mod.remove()
        log.debug('Removed tech support {0.shortlink}'.format(submission))

        return True

def submission_handler(submission):
    if check_if_ts(submission):
        return

    # If submission has no flair
    elif not submission.link_flair_text:
        log.debug('New submission: {0.title} {0.shortlink}'.format(submission))

        sleep_time_until_message = time_until_message - (time() - submission.created_utc)
        sleep_time_until_message = sleep_time_until_message if sleep_time_until_message > 0 else 0

        final_add_flair_message = add_flair_message.format(post_url=submission.shortlink)

        sleep(sleep_time_until_message)

        # Check if we have already sent a message
        sent_messages = [message for message in reddit.inbox.sent() if message.body == final_add_flair_message]
        if not sent_messages:
            if reddit.submission(submission.id).link_flair_text:
                return

            submission.author.message(add_flair_subject_line, final_add_flair_message)
            log.debug('Sent message for {0.title} {0.shortlink}'.format(submission))

            sleep_time_until_remove = time_until_remove - (time() - submission.created_utc)
            sleep_time_until_remove = sleep_time_until_remove if sleep_time_until_remove > 0 else time_until_remove

        else:
            log.debug('Already sent message for {0.title} {0.shortlink}'.format(submission))

            sleep_time_until_remove = time_until_remove - (time() - sent_messages[0].created_utc)
            sleep_time_until_remove = sleep_time_until_remove if sleep_time_until_remove > 0 else 0

        sleep(sleep_time_until_remove)

        if reddit.submission(submission.id).link_flair_text:
            check_if_ts(reddit.submission(submission.id))

            return

        submission.author.message(remove_post_subject_line, remove_post_message.format(post_url=submission.shortlink))
        submission.mod.remove()
        log.debug('Removed {0.title} {0.shortlink}'.format(submission))

@asyncio.coroutine
def main():
    '''
    Checks to see if a post has a flair, sends the user a message after
    `time_until_message seconds`, and removes it if there is no flair after
    `time_until_remove` seonds. Approves post if a flair is added. Refreshes every n seconds.
    '''
    while True:
        try:
            for submission in subreddit.stream.submissions():
                # print('NEW SUBMISSION: {}'.format(submission.title))

                # Creates background task
                ensure_future(loop.run_in_executor(executor, submission_handler(submission)))

        except Exception as e:
            log.critical('Error in submission_handler: {}'.format(e))

if __name__ == "__main__":
    # Puts main func into a loop and runs forever
    executor = ProcessPoolExecutor(2)
    loop = asyncio.get_event_loop()

    print("Registering Main\n")
    ensure_future(main())

    loop.run_forever()

    loop.close()
