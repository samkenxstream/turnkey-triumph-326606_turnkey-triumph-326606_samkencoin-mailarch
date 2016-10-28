'''This module implements the Zawinksi threading algorithm.
https://www.jwz.org/doc/threading.html
'''
import sys
import re

from collections import defaultdict
from operator import methodcaller

from mlarchive.archive.models import Message

CONTAINER_COUNT = 0
DEBUG = False
REFERENCE_RE = re.compile(r'<(.*?)>')

class Container(object):
    '''Used to construct the thread ordering then discarded'''
    global DEBUG
    def __init__(self, message=None):
        self.message = message
        self.parent = None
        self.child = None
        self.next = None
        self.depth = None

    def __str__(self):
        if self.parent:
            parent = self.parent.descriptor()
        else:
            parent = 'None'
        if self.child:
            child = self.child.descriptor()
        else:
            child = 'None'
        if self.next:
            next_ = self.next.descriptor()
        else:
            next_ = 'None'
        return 'parent:{},message:{},child:{},next:{}'.format(
            parent,
            self.descriptor(),
            child,
            next_)

    def descriptor(self):
        '''Descriptive text for display'''
        if self.is_empty():
            return 'Empty'
        else:
            subject = self.message.subject.encode('ascii','replace')
            return '{} ({})'.format(subject,self.message.msgid)

    def has_ancestor(self, target):
        '''Returns True if target is an ancestor'''
        if self.parent is None:
            return False
        elif self.parent == target:
            return True
        else:
            return self.parent.has_ancestor(target)

    def has_descendent(self, target):
        '''Returns True if the target is a descendent
        if self.child is None:
            return False
        elif self.child == target:
            return True
        else:
            return self.child.has_descendent(target)
        '''
        flat = [ x for x in self.walk() ]
        return target in flat

    def has_relative(self, target):
        '''Returns True if target is either an ancestor or descendent'''
        return self.has_descendent(target) or self.has_ancestor(target)

    def is_empty(self):
        '''Returns True if the container has no message'''
        return self.message is None

    def reverse_children(self):
        '''Reverse the children'''
        if self.child:
            prev = None
            kid = self.child
            rest = kid.next
            while kid:
                kid.next = prev

                # continue
                prev = kid
                kid = rest
                rest = None if rest is None else rest.next
            self.child = prev

            kid = self.child
            while kid:
                kid.reverse_children()
                kid = kid.next

    def sort_date(self):
        '''Returns the date to use for sorting.  Either the
        date of self.message or if this is a dummy container,
        the date of self.child.message
        '''
        if not self.is_empty():
            return self.message.date
        elif not self.child.is_empty():
            return self.child.message.date
        else:
            return None

    def walk(self):
        '''Walk the structure rooted at this container'''
        yield self
        if self.child:
            for container in self.child.walk():
                yield container
        if self.next:
            for container in self.next.walk():
                yield container


    def export(self, depth=0):
        '''Returns a generator that walks the tree and returns
        containers, assigning depth and order attributes
        '''
        self.depth = depth
        yield self
        if self.child:
            for container in self.child.export(depth=depth + 1):
                yield container
        if self.next:
            for container in self.next.export(depth=depth):
                yield container


def build_container(message, id_table, bogus_id_count):
    '''Builds Container objects for messages'''
    global DEBUG
    id = message.msgid
    container = id_table.get(id, None)
    if container:
        if container.is_empty():
            container.message = message
        else:
            # indicates a duplicate message-id
            id = "Bogus-id:{}".format(bogus_id_count)
            bogus_id_count += 1
            container = None

    if not container:
        container = Container(message)
        id_table[id] = container

    # 1.B
    # process references
    parent_ref = None
    # switch to message.get_references() after migration
    for reference_id in get_references(message):
        ref = id_table.get(reference_id, None)
        if not ref:
            ref = Container()
            id_table[reference_id] = ref
        
        # init list
        if DEBUG:
            print "in message: {}".format(message.msgid)
            print "checking reference: {}".format(reference_id)
            print "checking {} for descendent {}".format(parent_ref,ref)
        if (parent_ref and                  # there is a parent
                ref.parent is None and      # don't have a parent already
                parent_ref != ref and       # not a tight loop
                not parent_ref.has_relative(ref)):    # not a wide loop
            ref.parent = parent_ref
            ref.next = parent_ref.child
            parent_ref.child = ref

        parent_ref = ref

    # At this point parent_ref is set to the container of the last element
    # in the reference field.  make that be the parent of this container,
    # unless doing so would introduce circularity
    if parent_ref and (parent_ref == container or container.has_descendent(parent_ref)):
        parent_ref = None

    # If it has a parent already, that's there because we saw this message
    # in a references field, and presumed a parent based on the other
    # entries in that field.  Now that we have the actual message, we can
    # be more definitive, so throw away the old parent and use this new one.
    # Find this container in the parent's child-list and unlink it
    if container.parent:
        prev = None
        rest = container.parent.child
        while rest:
            if rest == container:
                break
            prev = rest
            rest = rest.next
        if rest is None:
            raise Exception("Couldn't find {} in  parent {}".format(container,container.parent))
        if prev is None:
            container.parent.child = container.next
        else:
            prev.next = container.next
        container.next = None
        container.parent = None

    if parent_ref:
        container.parent = parent_ref
        container.next = parent_ref.child
        parent_ref.child = container

    if DEBUG: 
        root = find_root(container)
        display_thread(root)
        s = raw_input("Press enter")


def build_subject_table(root_node):
    '''Builds a mapping of base subject (subject stripped of prefixes) to container'''
    subject_table = {}
    container = root_node.child
    while container:
        message = container.message
        if message is None:
            message = container.child.message
        if message.base_subject:
            existing = subject_table.get(message.base_subject)
            # add this container to the table if:
            # there is no container in the table with this subject
            if not existing:
                subject_table[message.base_subject] = container
            # this one is a dummy container and the old one is not: the
            # dummy one is more interesting as a root, so put it in the table instead
            elif container.is_empty() and not existing.is_empty():
                subject_table[message.base_subject] = container
            # the container in the table has a "Re:" version of this subjet,
            # and this container has a non-"Re:" version.
            # the non-"Re:" version is the more interesting of the two
            elif (existing.message and subject_is_reply(existing.message) and
                    (container.message and not subject_is_reply(container.message))):
                subject_table[message.base_subject] = container
        container = container.next

    return subject_table


def container_stats(parent, id_table):
    '''Show container stats for help in debugging'''
    empty = 0
    empty_top = 0
    empty_top_nochild = 0
    print "Length if id_table: {}".format(len(id_table))
    print "Length of walk(): {}".format(len(list(parent.walk())))
    for c in parent.walk():
        if c.is_empty():
            empty = empty + 1
            if c.parent is None:
                empty_top = empty_top + 1
                if c.child is None:
                    empty_top_nochild = empty_top_nochild + 1
                    print c
    print "Total empty: {}".format(empty)
    print "Total empty top-level: {}".format(empty_top)
    print "Total empty top-level no child: {}".format(empty_top_nochild)
    display_thread(parent)


def count_root_set(parent):
    '''Returns the number of top-level containers in the root set'''
    container = parent.child
    count = 1
    while container.next:
        count = count + 1
        container = container.next
    return count


def display_thread(parent, depth=0):
    '''Prints the thread.'''
    global CONTAINER_COUNT
    container = parent.child
    while container:
        CONTAINER_COUNT += 1
        if container.message:
            print '  ' * depth + container.message.subject + '  ' + container.message.date.strftime("%Y-%m-%d %H:%M")
        else:
            if container.parent is None:
                print "(Empty)"
            else:
                print container
                break
        if container.child:
            display_thread(container, depth=depth + 1)
        container = container.next


def find_root(node):
    '''Find the top level node'''
    if not node.parent:
        return node
    else:
        return find_root(node.parent)


def find_root_set(id_table):
    '''Find the root set of Containers and return a root node.
    A container is in the root set if it has no parents
    Takes mapping of message-id to containers
    '''
    root = Container()
    for container in id_table.values():
        if container.parent is None:
            if container.next is not None:
                raise Exception('container.next is {}'.format(container.next))
            container.next = root.child
            root.child = container
    return root


def gather_siblings(parent, siblings):
    '''Build mapping of parent to list of children containers'''
    container = parent.child
    while container:
        siblings[container.parent].append(container)
        if container.child:
            gather_siblings(container, siblings)
        container = container.next


def gather_subjects(root_node):
    '''If any two members of the root set have the same subject, merge them.
    This is so that messages which don't have References headers at all
    still get threaded (to the extent possible, at least.)
    '''
    subject_table = build_subject_table(root_node)

    if len(subject_table) == 0:
        return

    # subject_table is now populated with one entry for each subject which
    # occurs in the root set.  Now itereate over the root set, and gather
    # together the difference
    prev = None
    container = root_node.child
    rest = container.next
    while container:
        message = container.message
        if message is None:
            message = container.child.message
        subject = message.base_subject
        if subject:
            old = subject_table.get(subject)
            if old != container:
                # remove the "second" mssage from the root set.
                if prev is None:
                    root_node.child = container.next
                else:
                    prev.next = container.next
                container.next = None

                # if both are dummies, merge them
                if old.message is None and container.message is None:
                    tail = Container()
                    tail = old.child
                    while tail and tail.next:
                        tail = tail.next

                    tail.next = container.child
                    tail = container.child
                    while tail:
                        tail.parent = old
                        tail = tail.next
                    container.child = None
                # if old is empty and container is reply and old is not
                elif old.message is None or (container.message and subject_is_reply(container.message) and not subject_is_reply(old.message)):
                    container.parent = old
                    container.next = old.child
                    old.child = container
                # Otherwise, make a new dummy container and make both messages be a
                # child of it.  This catches the both-are-replies and neither-are-
                # replies cases, and makes them be siblings instead of asserting
                # a hiierarchical relationship which might not be true
                else:
                    new_container = Container()
                    new_container.message = old.message
                    new_container.child = old.child
                    tail = new_container.child
                    while tail:
                        tail.parent = new_container
                        tail = tail.next
                    old.message = None
                    old.child = None
                    container.parent = old
                    new_container.parent = old
                    old.child = container
                    container.next = new_container

                container = prev

        prev = container
        container = rest
        rest = None if rest is None else rest.next


def get_references(message):
    """Returns list of message-ids from References header"""
    # remove all whitespace
    refs = ''.join(message.references.split())
    refs = REFERENCE_RE.findall(refs)
    # de-dupe
    results = []
    for ref in refs:
        if ref not in results:
            results.append(ref)
    return results


def get_root_set(root_node):
    '''Returns generator of top-level nodes given root_node'''
    node = root_node.child
    while node:
        yield node
        node = node.next


def prune_empty_containers(parent):
    '''Walk through the threads and discard any empty container objects.
    After calling this, there will only be empty container objects
    at depth 0, and those will all have at least two kids
    '''
    prev = None
    container = parent.child
    if container is None:
        return
    next_ = container.next
    while container:
        # remove empty container with no children
        if container.message is None and container.child is None:
            if prev is None:
                parent.child = container.next
            else:
                prev.next = container.next
            container = prev

        elif (container.message is None and
              container.child and
              (container.parent or container.child.next is None)):
            tail = Container()
            kids = container.child
            if prev is None:
                parent.child = kids
            else:
                prev.next = kids

            # splice kids into the list in place of container
            tail = kids
            while tail.next:
                tail.parent = container.parent
                tail = tail.next

            tail.parent = container.parent
            tail.next = container.next

            next_ = kids
            container = prev

        elif container.child:
            prune_empty_containers(container)

        # continue with loop
        prev = container
        container = next_
        next_ = None if container is None else container.next


def process(queryset, display=False, debug=False):
    '''Takes a email list and returns the threaded structure as XXX'''
    global DEBUG
    DEBUG = debug

    id_table = {}       # message-ids to container
    bogus_id_count = 0  # use when there are duplicate message ids

    for message in queryset:
        build_container(message, id_table, bogus_id_count)

    # 2 Find the root set
    root_node = find_root_set(id_table)

    # 3 Discard id_table

    # 4 Prune Empty Containers
    prune_empty_containers(root_node)

    root_node.reverse_children()

    # 5 Group the root set by subject
    gather_subjects(root_node)

    # 7 Sort
    sort_thread(root_node)

    # debug
    if display:
        display_thread(root_node)
        print "messages count: {}".format(queryset.count())
        print "root set count: {}".format(count_root_set(root_node))
        print "total containers: {}".format(CONTAINER_COUNT)

    return root_node


def sort_siblings(siblings, reverse=False):
    '''Sort siblings (list of containers) by date.  Set new order
    by adjusting container.next.  Returns sorted list.
    * Has side-effects *
    '''
    sorted_siblings = sorted(siblings, key=methodcaller('sort_date'), reverse=reverse)
    sorted_siblings_iter = iter(sorted_siblings)
    prev = sorted_siblings_iter.next()
    for container in sorted_siblings_iter:
        prev.next = container
        prev = container
    else:
        prev.next = None
    return sorted_siblings


def sort_thread(root_node):
    '''Sort messages in the thread.  By default sort top-level, first
    message in thread, by date descending, then sub-thread siblings
    by date ascending
    '''
    siblings = defaultdict(list)
    gather_siblings(root_node, siblings)
    # sort root set (they have no parent)
    root_set = siblings.pop(None)
    root_node.child = sort_siblings(root_set,reverse=True)[0]
    # sort remaining siblings
    for parent,children in siblings.items():
        if len(children) > 1:
            parent.child = sort_siblings(children)[0]


def subject_is_reply(message):
    '''Returns True if the subject indicates this message is a reply'''
    return message.subject.startswith('Re: ')
