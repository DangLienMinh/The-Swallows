import random
import sys

from swallows.engine.events import Event

### TOPICS ###

# a "topic" is just what a character has recently had addressed to
# them.  It could be anything, not just words, by another character
# (for example, a gesture.)

class Topic(object):
    def __init__(self, originator, subject=None):
        self.originator = originator
        self.subject = subject


class GreetTopic(Topic):
    pass


class SpeechTopic(Topic):
    pass


class QuestionTopic(Topic):
    pass


### BELIEFS ###

#
# a belief is something an Animate believes.  they come in a few types:
#
# - a belief that an object is somewhere
#   - because they saw it there (memory)
#   - because some other character told them it was there
# - a belief that they should do something (a goal)
# - a belief that another Animate believes something
#
# of course, any particular belief may turn out not to be true
#

# abstract base class
class Belief(object):
    def __init__(self, subject):    # kind of silly for an ABC to have a constructor, but ok
        self.subject = subject      # the thing we believe something about

    def __str__(self):
        raise NotImplementedError


class ItemLocationBelief(Belief):   # formerly "Memory"
    def __init__(self, subject, location, informant=None, concealer=None):
        self.subject = subject      # the thing we think is somewhere
        self.location = location    # the place we think it is
        self.informant = informant  # the actor who told us about it
        self.concealer = concealer  # the actor who we think hid it ther

    def __str__(self):
        return "%s is in %s" % (
            self.subject.render([]),
            self.location.render([])
        )
        #if .
        #    print ".oO{ I hid it there }"


# this could itself have several subclasses
class GoalBelief(Belief):
    def __init__(self, subject, phrase):
        self.subject = subject   # the thing we would like to do something about
        self.phrase = phrase     # human-readable description


# oh dear
class BeliefBelief(Belief):
    def __init__(self, subject, belief):
        assert isinstance(subject, Animate)
        assert isinstance(belief, Belief)
        self.subject = subject   # the animate we think holds the belief
        self.belief = belief     # the belief we think they hold


### ACTORS (objects in the world) ###

class Actor(object):
    def __init__(self, name, location=None, collector=None):
        self.name = name
        self.collector = collector
        self.contents = set()
        self.enter = ""
        self.location = None
        if location is not None:
            self.move_to(location)

    def notable(self):
        return self.treasure() or self.weapon() or self.animate() or self.horror()

    def treasure(self):
        return False

    def weapon(self):
        return False

    def horror(self):
        return False

    def takeable(self):
        return False

    def animate(self):
        return False

    def container(self):
        return False

    def article(self):
        return 'the'

    def posessive(self):
        return "its"

    def accusative(self):
        return "it"

    def pronoun(self):
        return "it"

    def was(self):
        return "was"

    def is_(self):
        return "is"

    def emit(self, *args, **kwargs):
        if self.collector:
            self.collector.collect(Event(*args, **kwargs))

    def move_to(self, location):
        if self.location:
            self.location.contents.remove(self)
        self.location = location
        self.location.contents.add(self)

    def render(self, participants):
        name = self.name
        if participants:
            subject = participants[0]
            posessive = subject.name + "'s"
            name = name.replace(posessive, subject.posessive())
        article = self.article()
        if not article:
            return name
        return '%s %s' % (article, name)

    def indefinite(self):
        article = 'a'
        if self.name.startswith(('a', 'e', 'i', 'o', 'u')):
            article = 'an'
        return '%s %s' % (article, self.name)


### some mixins for Actors ###

class ProperMixin(object):
    def article(self):
        return ''


class PluralMixin(object):
    def posessive(self):
        return "their"

    def accusative(self):
        return "them"

    def pronoun(self):
        return "they"

    def indefinite(self):
        article = 'some'
        return '%s %s' % (article, self.name)

    def was(self):
        return "were"

    def is_(self):
        return "are"


class MasculineMixin(object):
    def posessive(self):
        return "his"

    def accusative(self):
        return "him"

    def pronoun(self):
        return "he"


class FeminineMixin(object):
    def posessive(self):
        return "her"

    def accusative(self):
        return "her"

    def pronoun(self):
        return "she"


### ANIMATE OBJECTS ###

class Animate(Actor):
    def __init__(self, name, location=None, collector=None):
        Actor.__init__(self, name, location=location, collector=None)
        self.topic = None
        # map of actors to sets of Beliefs about them
        self.beliefs = {}
        self.desired_items = set()
        # this should really be *derived* from having a recent memory
        # of seeing a dead body in the bathroom.  but for now,
        self.nerves = 'calm'
        # this, too, should be more sophisticated.
        # it is neither a memory, nor a belief, but a judgment, and
        # eventually possibly a goal.
        # hash maps Actors to strings
        self.what_to_do_about = {}
        self.other_decision_about = {}

    def animate(self):
        return True

    # for debugging
    def dump_beliefs(self):
        for subject in self.beliefs:
            print ".oO{ %s }" % self.beliefs[subject]
        print "desired items:", repr(self.desired_items)
        print "decisions:", repr(self.what_to_do_about)
        print "knowledge of others' decisions:", repr(self.other_decision_about)

    def remember(self, thing, location, informant=None, concealer=None):
        """Update this Animate's beliefs to include a belief that the
        given thing is located at the given location.

        """
        assert isinstance(thing, Actor)
        belief_set = self.beliefs.get(thing, set())
        for belief in belief_set:
            if isinstance(belief, ItemLocationBelief):
                # update it
                belief.location = location
                belief.informant = informant
                belief.concealer = concealer
                return
        # if we're still here, we didn't have any such belief, so add one
        belief = ItemLocationBelief(
            thing, location, informant=informant, concealer=concealer
        )
        belief_set.add(belief)
        self.beliefs[thing] = belief_set

    def recall(self, thing):
        """Return an ItemLocationBelief about this thing, or None."""
        assert isinstance(thing, Actor)
        belief_set = self.beliefs.get(thing, set())
        for belief in belief_set:
            if isinstance(belief, ItemLocationBelief):
                return belief
        return None

    def forget_location(self, thing):
        assert isinstance(thing, Actor)
        belief_set = self.beliefs.get(thing, set())
        target_beliefs = set()
        for belief in belief_set:
            if isinstance(belief, ItemLocationBelief):
                target_beliefs.add(belief)
        assert len(target_beliefs) in (0, 1)
        for belief in target_beliefs:
            belief_set.remove(belief)

    def address(self, other, topic, phrase, participants=None):
        if participants is None:
            participants = [self, other]
        other.topic = topic
        self.emit(phrase, participants)

    def greet(self, other, phrase, participants=None):
        self.address(other, GreetTopic(self), phrase, participants)

    def speak_to(self, other, phrase, participants=None, subject=None):
        self.address(other, SpeechTopic(self, subject=subject), phrase, participants)

    def question(self, other, phrase, participants=None, subject=None):
        self.address(other, QuestionTopic(self, subject=subject), phrase, participants)

    def place_in(self, location):
        # like move_to but quieter; for setting up scenes etc
        if self.location is not None:
            self.location.contents.remove(self)
        self.location = location
        self.location.contents.add(self)
        # this is needed so that the Editor knows where the character starts
        # (it is possible a future Editor might be able to strip out
        # instances of these that aren't informative, though)
        self.emit("<1> <was-1> in <2>", [self, self.location])
        # a side-effect of the following code is, if they start in a location
        # with a horror,they don't react to it.  They probably should.
        for x in self.location.contents:
            if x == self:
                continue
            if x.notable():
                self.emit("<1> saw <2>", [self, x])
                self.remember(x, self.location)

    def move_to(self, location):
        assert(location != self.location)
        assert(location is not None)
        for x in self.location.contents:
            # otherwise we get "Bob saw Bob leave the room", eh?
            if x is self:
                continue
            if x.animate():
                x.emit("<1> saw <2> leave the %s" % x.location.noun(), [x, self])
        if self.location is not None:
            self.location.contents.remove(self)
        self.location = location
        assert self not in self.location.contents
        self.location.contents.add(self)
        self.emit("<1> went to <2>", [self, self.location])

    def point_at(self, other, item):
        # it would be nice if there was some way to
        # indicate the revolver as part of the Topic which will follow,
        # or otherwise indicate the context as "at gunpoint"

        assert self.location == other.location
        assert item.location == self
        self.emit("<1> pointed <3> at <2>",
            [self, other, item])
        for actor in self.location.contents:
            if actor.animate():
                actor.remember(item, self)

    def put_down(self, item):
        assert(item.location == self)
        self.emit("<1> put down <2>", [self, item])
        item.move_to(self.location)
        for actor in self.location.contents:
            if actor.animate():
                actor.remember(item, self.location)

    def pick_up(self, item):
        assert(item.location == self.location)
        self.emit("<1> picked up <2>", [self, item])
        item.move_to(self)
        for actor in self.location.contents:
            if actor.animate():
                actor.remember(item, self)

    def give_to(self, other, item):
        assert(item.location == self)
        assert(self.location == other.location)
        self.emit("<1> gave <3> to <2>", [self, other, item])
        item.move_to(other)
        for actor in self.location.contents:
            if actor.animate():
                actor.remember(item, other)

    def wander(self):
        self.move_to(
            self.location.exits[
                random.randint(0, len(self.location.exits)-1)
            ]
        )

    def live(self):
        """This gets called on each turn an animate moves.
        
        You need to implement this for particular animates.
        
        """
        raise NotImplementedError(
            'Please implement %s.live()' % self.__class__.__name__
        )


class Male(MasculineMixin, ProperMixin, Animate):
    pass


class Female(FeminineMixin, ProperMixin, Animate):
    pass


### LOCATIONS ###

class Location(Actor):
    def __init__(self, name, enter="went to", noun="room"):
        self.name = name
        self.enter = enter
        self.contents = set()
        self.exits = []
        self.noun_ = noun

    def noun(self):
        return self.noun_

    def set_exits(self, *exits):
        for exit in exits:
            assert isinstance(exit, Location)
        self.exits = exits


class ProperLocation(ProperMixin, Location):
    pass


### OTHER INANIMATE OBJECTS ###

class Item(Actor):
    def takeable(self):
        return True


class Weapon(Item):
    def weapon(self):
        return True


class Container(Actor):
    def container(self):
        return True


class ProperContainer(ProperMixin, Container):
    pass


class Treasure(Item):
    def treasure(self):
        return True


class PluralTreasure(PluralMixin, Treasure):
    pass


class Horror(Actor):
    def horror(self):
        return True
