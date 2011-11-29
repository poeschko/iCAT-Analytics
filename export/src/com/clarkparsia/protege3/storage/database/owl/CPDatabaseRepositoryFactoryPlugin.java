package com.clarkparsia.protege3.storage.database.owl;

import java.sql.SQLException;
import java.util.List;
import java.util.logging.Level;
import java.util.logging.Logger;

import edu.stanford.smi.protege.storage.database.DatabaseProperty;
import edu.stanford.smi.protege.util.Log;
import edu.stanford.smi.protegex.owl.model.OWLModel;
import edu.stanford.smi.protegex.owl.repository.Repository;
import edu.stanford.smi.protegex.owl.repository.factory.RepositoryFactoryPlugin;

public class CPDatabaseRepositoryFactoryPlugin implements RepositoryFactoryPlugin {
    private final static transient Logger log = Log.getLogger(CPDatabaseRepositoryFactoryPlugin.class);

    public Repository createRepository(OWLModel model,
                                       String repositoryDescriptor) {
        try {
            return new CPDatabaseRepository(repositoryDescriptor);
        }
        catch (ClassNotFoundException e) {
            log.warning("Database repository driver class not found = " + e);
            if (log.isLoggable(Level.FINE)) {
                log.log(Level.FINE, "Exception caught initializing the database repository", e);
            }
            return null;
        }
        catch (SQLException e) {
            log.warning("SQL error caught initializing the database repository" + e);
            if (log.isLoggable(Level.FINE)) {
                log.log(Level.FINE, "SQL error caught initializing the database repository", e);
            }
            return null;
        }
    }

    public boolean isSuitable(OWLModel model, String repositoryDescriptor) {
        if (repositoryDescriptor.startsWith(CPDatabaseRepository.REPOSITORY_DESCRIPTOR_PREFIX)) {
            try {
                List<String> fields = CPDatabaseRepository.parse(repositoryDescriptor);
                Class.forName(fields.get(CPDatabaseRepository.getDBPropertyIndex(DatabaseProperty.DRIVER_PROPERTY)));
                return  fields.size() > CPDatabaseRepository.DATABASE_FIELDS.length;
            }
            catch (Throwable t) {
                if (log.isLoggable(Level.FINE)) {
                    log.fine("Repository descriptor = " + repositoryDescriptor);
                    log.log(Level.FINE, "Exception caught figuring out if database repository was applicable", t);
                }
                return false;
            }
        }
        return false;
    }

}
