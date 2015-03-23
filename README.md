# SlackPoll
Add a basic polling integration to slack channels. It currently allows for one poll per channel at a given time. You can configure it with a timeout to close a poll after a certain amount of time.

### Start a poll

The basic syntax is `/poll timeout [time in minutes] topic [Question] options [options]`, where the timeout is an optional field and the options are delineated by a triple dash `---`. During poll creation the person who started the poll is identified, so if you would like to start a new poll contact the other user and get them to close theirs.

An example of asking the team what you should do for lunch could be like this. This poll would be open for 5 minutes.

`/poll timeout 5 topic What should we get for lunch? options Burgers --- Pizza --- Seafood`

![Initial Poll Command](screenshots/startpolltext.PNG "Initial Poll Command")

![Initial Poll](screenshots/initialpoll.PNG "Initial Poll")

--

### Casting a vote

Casting a vote is as easy as `/poll cast [option number]`. Each person is only allowed to vote once. Voting more than once will just change your vote to whatever you voted for last.

--

### How many people have voted in my poll?

If you would like to see how many votes there have been in the current poll just run `/poll count`.

--

### Closing a poll

Closing a poll is simple but it is limited to the person that started the poll. To close a poll simply run `/poll close` in the channel that you started your poll in. The results of your poll will then be posted with 

![Closing Poll](screenshots/closedpoll.PNG "Closing Poll")


